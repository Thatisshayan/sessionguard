/**
 * src/pages/LiveMonitor.tsx
 * --------------------------
 * Real-time live session monitoring.
 * Start a run → watch events stream in → pause/resume/stop.
 * Polls /live/{run_id}/events every second for new events.
 *
 * Maturity: Working Prototype — mock mode fully working.
 *           Screen mode: connects to real OCR if machine supports it.
 */

import { useEffect, useState, useRef, useCallback } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import {
  getSessions, startLiveRun, pauseLiveRun, resumeLiveRun,
  stopLiveRun, getLiveRun, getLiveEvents,
} from '../services/api'
import type { Session, LiveRun, LiveEvent } from '../services/api'
import LiveCoach from '../components/LiveCoach'

interface ChartPoint {
  index: number
  net_delta: number
  cumulative: number
  confidence: number
  risk_flag: boolean
}

const STATUS_COLOR: Record<string, string> = {
  running: 'var(--accent-green)',
  paused:  'var(--accent-amber)',
  stopped: 'var(--text-muted)',
}

export default function LiveMonitor() {
  const [sessions,   setSessions]   = useState<Session[]>([])
  const [sessionId,  setSessionId]  = useState<number | null>(null)
  const [mode,       setMode]       = useState<'mock' | 'screen'>('mock')
  const [run,        setRun]        = useState<LiveRun | null>(null)
  const [events,     setEvents]     = useState<LiveEvent[]>([])
  const [chartData,  setChartData]  = useState<ChartPoint[]>([])
  const [error,      setError]      = useState('')
  const [starting,   setStarting]   = useState(false)
  const [coachStyle, setCoachStyle] = useState<'strict'|'balanced'|'supportive'>('balanced')

  const pollRef   = useRef<ReturnType<typeof setInterval> | null>(null)
  const lastIdRef = useRef(0)
  const cumRef    = useRef(0)

  useEffect(() => {
    getSessions({ limit: 100 }).then(setSessions)
  }, [])

  // ── Polling ─────────────────────────────────────────────────────────────────
  const startPolling = useCallback((runId: number) => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const [newEvents, runStatus] = await Promise.all([
          getLiveEvents(runId, lastIdRef.current),
          getLiveRun(runId),
        ])
        setRun(runStatus)

        if (newEvents.length > 0) {
          lastIdRef.current = newEvents[newEvents.length - 1].id
          setEvents(prev => [...prev, ...newEvents].slice(-100))  // keep last 100

          const newPoints: ChartPoint[] = newEvents.map(ev => {
            const p    = ev.payload as any
            const net  = p.net_delta ?? (p.win_amount ?? 0) - (p.bet_amount ?? 0)
            cumRef.current = round(cumRef.current + net)
            return {
              index:      p.event_index ?? 0,
              net_delta:  round(net),
              cumulative: cumRef.current,
              confidence: p.ocr_confidence ?? 1,
              risk_flag:  p.risk_flag ?? false,
            }
          })
          setChartData(prev => [...prev, ...newPoints].slice(-80))
        }

        if (runStatus.status === 'stopped') stopPolling()
      } catch { /* server may not be up */ }
    }, 1000)
  }, [])

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  useEffect(() => () => stopPolling(), [])

  const round = (n: number) => Math.round(n * 100) / 100

  // ── Controls ─────────────────────────────────────────────────────────────────
  const handleStart = async () => {
    if (!sessionId) { setError('Select a session first.'); return }
    setError(''); setStarting(true)
    try {
      const r = await startLiveRun({ session_id: sessionId, mode, tick_interval: 1.5 })
      const runData = await getLiveRun(r.run_id)
      setRun(runData)
      setEvents([]); setChartData([])
      lastIdRef.current = 0; cumRef.current = 0
      startPolling(r.run_id)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Failed to start live run.')
    } finally { setStarting(false) }
  }

  const handlePause = async () => {
    if (!run) return
    await pauseLiveRun(run.id)
    setRun(r => r ? { ...r, status: 'paused' } : r)
  }

  const handleResume = async () => {
    if (!run) return
    await resumeLiveRun(run.id)
    setRun(r => r ? { ...r, status: 'running' } : r)
  }

  const handleStop = async () => {
    if (!run) return
    stopPolling()
    await stopLiveRun(run.id)
    setRun(r => r ? { ...r, status: 'stopped' } : r)
  }

  const isRunning = run?.status === 'running'
  const isPaused  = run?.status === 'paused'
  const isStopped = !run || run.status === 'stopped'

  const sel: React.CSSProperties = {
    background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
    color: 'var(--text-primary)', padding: '8px 12px',
    borderRadius: 'var(--radius-sm)', fontSize: 13,
  }

  // Recent events in display order (newest first)
  const recentEvents = [...events].reverse().slice(0, 20)

  return (
    <div style={{ padding: 'var(--page-margin)' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 'var(--space-8)' }}>Live Monitor</h1>

      {/* ── Controls ─────────────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          {/* Session selector */}
          <div style={{ flex: 2, minWidth: 200 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Session</div>
            <select value={sessionId ?? ''} onChange={e => setSessionId(Number(e.target.value) || null)}
              style={{ ...sel, width: '100%' }} disabled={!isStopped}>
              <option value="">— Select a session —</option>
              {sessions.map(s => (
                <option key={s.id} value={s.id}>#{s.id} · {s.game_name} · {s.date}</option>
              ))}
            </select>
          </div>

          {/* Mode selector */}
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Mode</div>
            <select value={mode} onChange={e => setMode(e.target.value as 'mock' | 'screen')}
              style={sel} disabled={!isStopped}>
              <option value="mock">Mock (synthetic events)</option>
              <option value="screen">Screen (live OCR)</option>
            </select>
          </div>

          {/* Coach style */}
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>🥊 Coach Style</div>
            <select value={coachStyle} onChange={e => setCoachStyle(e.target.value as any)}
              style={sel} disabled={!isStopped}>
              <option value="strict">Strict — no sugar-coating</option>
              <option value="balanced">Balanced — honest and calm</option>
              <option value="supportive">Supportive — patient and kind</option>
            </select>
          </div>

          {/* Run status */}
          {run && (
            <div style={{ display: 'flex', flex: 1, alignItems: 'center', gap: 12 }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 700, color: STATUS_COLOR[run.status] }}>
                ●
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, color: STATUS_COLOR[run.status] }}>
                  {run.status.toUpperCase()}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Run #{run.id} · {run.event_index} events · {run.mode}
                </div>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 8 }}>
            {isStopped && (
              <button onClick={handleStart} disabled={starting || !sessionId}
                style={{ background: 'var(--accent-green)', border: 'none', color: '#fff', padding: '9px 22px', borderRadius: 'var(--radius-sm)', cursor: sessionId ? 'pointer' : 'not-allowed', fontSize: 13, fontWeight: 600, opacity: sessionId ? 1 : 0.5 }}>
                {starting ? 'Starting…' : '▶ Start'}
              </button>
            )}
            {isRunning && (
              <>
                <button onClick={handlePause}
                  style={{ background: 'var(--accent-amber)', border: 'none', color: '#000', padding: '9px 22px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
                  ⏸ Pause
                </button>
                <button onClick={handleStop}
                  style={{ background: 'var(--severity-critical)', border: 'none', color: '#fff', padding: '9px 22px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
                  ⏹ Stop
                </button>
              </>
            )}
            {isPaused && (
              <>
                <button onClick={handleResume}
                  style={{ background: 'var(--accent-green)', border: 'none', color: '#fff', padding: '9px 22px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
                  ▶ Resume
                </button>
                <button onClick={handleStop}
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '9px 22px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>
                  ⏹ Stop
                </button>
              </>
            )}
          </div>
        </div>
        {error && <div style={{ marginTop: 12, color: 'var(--severity-critical)', fontSize: 13 }}>{error}</div>}
        {mode === 'screen' && isStopped && (
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--accent-amber)', padding: '8px 12px', background: 'rgba(245,158,11,0.08)', borderRadius: 'var(--radius-sm)' }}>
            ⚠ Screen mode captures your display and runs OCR. Ensure the game window is visible and the correct profile ROI is configured.
          </div>
        )}
      </div>

      {/* ── Live chart ───────────────────────────────────────────────────── */}
      {(run && chartData.length > 0) && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
              Cumulative Net — Live
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: (chartData.at(-1)?.cumulative ?? 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {(chartData.at(-1)?.cumulative ?? 0) >= 0 ? '+' : ''}${chartData.at(-1)?.cumulative ?? 0}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="liveGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="var(--accent-blue)" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" />
              <XAxis dataKey="index" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: 'Tick', fill: 'var(--text-muted)', fontSize: 10, position: 'insideBottomRight', offset: -10 }} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }}
                formatter={(v: any, name: string) => [`$${Number(v).toFixed(2)}`, name === 'cumulative' ? 'Cumulative Net' : name]} />
              <ReferenceLine y={0} stroke="var(--text-muted)" strokeDasharray="4 4" />
              <Area type="monotone" dataKey="cumulative" stroke="var(--accent-blue)" fill="url(#liveGrad)" strokeWidth={2} dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Event feed ───────────────────────────────────────────────────── */}
      {run && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 'var(--gutter)' }}>
          {/* Recent event table */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--bg-border)', fontSize: 13, fontWeight: 600, display: 'flex', justifyContent: 'space-between' }}>
              <span>Event Feed</span>
              {isRunning && <span style={{ fontSize: 11, color: 'var(--accent-green)' }}>● LIVE</span>}
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--bg-border)', background: 'var(--bg-elevated)' }}>
                  {['#', 'Type', 'Bet', 'Win', 'Net', 'Confidence', 'Risk'].map(h => (
                    <th key={h} style={{ padding: '6px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 10, textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentEvents.map(ev => {
                  const p   = ev.payload as any
                  const net = p.net_delta ?? (p.win_amount ?? 0) - (p.bet_amount ?? 0)
                  return (
                    <tr key={ev.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                      <td style={{ padding: '7px 12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{p.event_index}</td>
                      <td style={{ padding: '7px 12px' }}><span className="badge badge-info" style={{ fontSize: 9 }}>{ev.event_type}</span></td>
                      <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>${(p.bet_amount ?? 0).toFixed(2)}</td>
                      <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: (p.win_amount ?? 0) > 0 ? 'var(--accent-green)' : 'var(--text-muted)', fontWeight: (p.win_amount ?? 0) > 0 ? 700 : 400 }}>
                        {(p.win_amount ?? 0) > 0 ? `$${(p.win_amount).toFixed(2)}` : '—'}
                      </td>
                      <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: net >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {net >= 0 ? '+' : ''}${net.toFixed(2)}
                      </td>
                      <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: (p.ocr_confidence ?? 1) < 0.75 ? 'var(--severity-warning)' : 'var(--text-muted)', fontSize: 11 }}>
                        {((p.ocr_confidence ?? 1) * 100).toFixed(0)}%
                      </td>
                      <td style={{ padding: '7px 12px' }}>
                        {p.risk_flag && <span className="badge badge-warning" style={{ fontSize: 9 }}>risk</span>}
                      </td>
                    </tr>
                  )
                })}
                {recentEvents.length === 0 && (
                  <tr><td colSpan={7} style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                    {isRunning ? 'Waiting for events…' : 'No events yet.'}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Stats sidebar */}
          <div>
            {/* AI Live Coach */}
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <LiveCoach
                runId={run?.id ?? null}
                running={run?.status === 'running'}
                style={coachStyle}
              />
            </div>
            <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Run Stats</div>
              {[
                ['Run ID',       `#${run.id}`],
                ['Status',       run.status.toUpperCase()],
                ['Events',       String(run.event_index)],
                ['Mode',         run.mode],
                ['Tick Interval',`${run.tick_interval}s`],
                ['Started',      run.started_at?.slice(11, 19) ?? '—'],
              ].map(([label, val]) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontSize: 11 }}>{val}</span>
                </div>
              ))}
            </div>

            {/* Risk summary from chart data */}
            {chartData.length > 0 && (() => {
              const riskCount = chartData.filter(d => d.risk_flag).length
              const avgConf   = chartData.reduce((a, d) => a + d.confidence, 0) / chartData.length
              const totalNet  = chartData.at(-1)?.cumulative ?? 0
              return (
                <div className="card">
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Live Analysis</div>
                  {[
                    ['Risk Events',   `${riskCount}/${chartData.length}`, riskCount > 5 ? 'var(--severity-warning)' : 'var(--text-primary)'],
                    ['Avg Confidence',`${(avgConf * 100).toFixed(0)}%`,  avgConf < 0.75 ? 'var(--severity-warning)' : 'var(--accent-green)'],
                    ['Cumulative Net',`${totalNet >= 0 ? '+' : ''}$${totalNet}`, totalNet >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'],
                  ].map(([label, val, color]) => (
                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 12 }}>
                      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: color ?? 'var(--text-primary)', fontWeight: 700, fontSize: 11 }}>{val}</span>
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>
        </div>
      )}

      {!run && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 280, color: 'var(--text-muted)', flexDirection: 'column', gap: 16 }}>
          <div style={{ fontSize: 48 }}>⏱</div>
          <div style={{ fontSize: 14 }}>Select a session and press Start to begin live monitoring</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', maxWidth: 400, textAlign: 'center' }}>
            Mock mode generates realistic synthetic events. Screen mode captures your display and runs real OCR — requires the game window to be visible.
          </div>
        </div>
      )}
    </div>
  )
}
