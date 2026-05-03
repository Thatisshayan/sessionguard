/**
 * src/pages/Compare.tsx
 * Maturity: Working Prototype — real comparison with charts and narrative.
 */
import { useEffect, useState } from 'react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { compareSessions, getSessions } from '../services/api'
import type { Session, CompareResult } from '../services/api'

const METRICS: { key: keyof Session; label: string; format: (v: any) => string; good: 'high' | 'low' }[] = [
  { key: 'rtp',           label: 'RTP %',         format: v => `${v}%`,   good: 'high' },
  { key: 'net_result',    label: 'Net Result',     format: v => `$${v?.toFixed(2)}`, good: 'high' },
  { key: 'spins',         label: 'Spins',          format: v => String(v), good: 'high' },
  { key: 'biggest_win',   label: 'Biggest Win',    format: v => `$${v?.toFixed(2)}`, good: 'high' },
  { key: 'losing_streak', label: 'Losing Streak',  format: v => String(v), good: 'low'  },
  { key: 'total_bets',    label: 'Total Wagered',  format: v => `$${v?.toFixed(2)}`, good: 'high' },
]

function MetricWinner({ sessions, metric }: { sessions: Session[]; metric: typeof METRICS[number] }) {
  const values = sessions.map(s => Number(s[metric.key] ?? 0))
  const best   = metric.good === 'high' ? Math.max(...values) : Math.min(...values)
  return (
    <div style={{ marginBottom: 'var(--space-4)' }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {metric.label}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {sessions.map((s, i) => {
          const val    = Number(s[metric.key] ?? 0)
          const isWin  = val === best
          return (
            <div key={s.id} style={{
              flex: 1, padding: '10px 12px', borderRadius: 'var(--radius-sm)',
              background: isWin ? 'rgba(59,130,246,0.1)' : 'var(--bg-elevated)',
              border: `1px solid ${isWin ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
            }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.name}
              </div>
              <div style={{ fontSize: 15, fontFamily: 'var(--font-mono)', fontWeight: 700, color: isWin ? 'var(--accent-blue)' : 'var(--text-primary)' }}>
                {metric.format(val)}
              </div>
              {isWin && <div style={{ fontSize: 10, color: 'var(--accent-blue)', marginTop: 2 }}>▲ Best</div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Compare() {
  const [allSessions, setAllSessions] = useState<Session[]>([])
  const [selected,    setSelected]    = useState<number[]>([])
  const [result,      setResult]      = useState<CompareResult | null>(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState('')

  useEffect(() => {
    getSessions({ limit: 100 }).then(setAllSessions)
  }, [])

  const toggleSession = (id: number) => {
    setSelected(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
    setResult(null)
  }

  const run = async () => {
    if (selected.length < 2) { setError('Select at least 2 sessions.'); return }
    setLoading(true); setError('')
    try {
      const r = await compareSessions(selected)
      setResult(r)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Comparison failed.')
    } finally { setLoading(false) }
  }

  // Radar chart data — normalise 0-100
  const radarData = result ? METRICS.map(m => {
    const vals = result.sessions.map(s => Number(s[m.key] ?? 0))
    const max  = Math.max(...vals, 1)
    const obj: any = { metric: m.label }
    result.sessions.forEach(s => {
      obj[s.name] = Math.round((Number(s[m.key] ?? 0) / max) * 100)
    })
    return obj
  }) : []

  const COLORS = ['var(--accent-blue)', 'var(--accent-green)', 'var(--accent-amber)', 'var(--accent-purple)']

  return (
    <div style={{ padding: 'var(--page-margin)' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 'var(--space-8)' }}>Compare Lab</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 'var(--space-6)', alignItems: 'start' }}>

        {/* ── Session selector ─────────────────────────────────────────── */}
        <div>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--bg-border)', fontSize: 13, fontWeight: 600 }}>
              Select Sessions
            </div>
            <div style={{ maxHeight: 420, overflowY: 'auto' }}>
              {allSessions.map(s => {
                const sel = selected.includes(s.id)
                return (
                  <div key={s.id}
                    onClick={() => toggleSession(s.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '10px 16px', cursor: 'pointer',
                      background: sel ? 'rgba(59,130,246,0.08)' : 'transparent',
                      borderBottom: '1px solid var(--bg-border)',
                      borderLeft: sel ? '3px solid var(--accent-blue)' : '3px solid transparent',
                      transition: 'all var(--transition-fast)',
                    }}>
                    <div style={{
                      width: 16, height: 16, borderRadius: 4,
                      border: `1px solid ${sel ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
                      background: sel ? 'var(--accent-blue)' : 'transparent',
                      flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 10, color: '#fff',
                    }}>
                      {sel && '✓'}
                    </div>
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ fontSize: 12, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {s.game_name}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {s.date} · {s.net_result >= 0 ? '+' : ''}${s.net_result.toFixed(2)} · {s.rtp}%
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
            <div style={{ padding: '12px 16px', borderTop: '1px solid var(--bg-border)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 10 }}>
                {selected.length} selected {selected.length >= 2 ? '✓' : `(need ${2 - selected.length} more)`}
              </div>
              <button onClick={run} disabled={loading || selected.length < 2}
                style={{
                  width: '100%', background: selected.length >= 2 ? 'var(--accent-blue)' : 'var(--bg-elevated)',
                  border: 'none', color: selected.length >= 2 ? '#fff' : 'var(--text-muted)',
                  padding: '10px', borderRadius: 'var(--radius-sm)', cursor: selected.length >= 2 ? 'pointer' : 'not-allowed',
                  fontSize: 13, fontWeight: 600, transition: 'all var(--transition-fast)',
                }}>
                {loading ? 'Comparing…' : 'Run Comparison'}
              </button>
              {selected.length > 0 && (
                <button onClick={() => { setSelected([]); setResult(null) }}
                  style={{ width: '100%', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12, marginTop: 8, padding: 4 }}>
                  Clear selection
                </button>
              )}
            </div>
          </div>
          {error && <div style={{ marginTop: 8, color: 'var(--severity-critical)', fontSize: 12 }}>{error}</div>}
        </div>

        {/* ── Results ──────────────────────────────────────────────────── */}
        <div>
          {!result && !loading && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: 'var(--text-muted)', fontSize: 13, flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 40 }}>⇌</div>
              <div>Select 2 or more sessions and click Compare</div>
            </div>
          )}

          {result && (
            <>
              {/* Narrative */}
              <div className="card" style={{ marginBottom: 'var(--space-6)', borderColor: 'var(--accent-blue)' }}>
                <div style={{ fontSize: 11, color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Analysis Narrative</div>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>{result.narrative}</p>
              </div>

              {/* Radar chart */}
              <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
                  Performance Radar (normalised 0–100)
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="var(--bg-border)" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                    <PolarRadiusAxis tick={{ fill: 'var(--text-muted)', fontSize: 9 }} domain={[0, 100]} />
                    {result.sessions.map((s, i) => (
                      <Radar key={s.id} name={s.name} dataKey={s.name}
                        stroke={COLORS[i % COLORS.length]}
                        fill={COLORS[i % COLORS.length]}
                        fillOpacity={0.1} strokeWidth={2} />
                    ))}
                    <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              {/* Metric-by-metric breakdown */}
              <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-6)' }}>
                  Metric Breakdown
                </div>
                {METRICS.map(m => (
                  <MetricWinner key={String(m.key)} sessions={result.sessions as Session[]} metric={m} />
                ))}
              </div>

              {/* Diff summary */}
              <div className="card">
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
                  Diff Summary
                </div>
                {[
                  ['RTP Range',    `${result.diff.rtp_range?.min}% – ${result.diff.rtp_range?.max}%`,   `Δ ${result.diff.rtp_range?.delta}%`],
                  ['Net Range',    `$${result.diff.net_range?.min?.toFixed(2)} – $${result.diff.net_range?.max?.toFixed(2)}`, `Δ $${result.diff.net_range?.delta?.toFixed(2)}`],
                  ['Streak Range', `${result.diff.streak_range?.min} – ${result.diff.streak_range?.max} spins`, `Δ ${result.diff.streak_range?.delta}`],
                  ['Best RTP',     result.diff.best_rtp_session,  '▲'],
                  ['Worst RTP',    result.diff.worst_rtp_session, '▼'],
                  ['Best Net',     result.diff.best_net_session,  '▲'],
                ].map(([label, val, aside]) => (
                  <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 13 }}>
                    <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                      <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>{val}</span>
                      <span style={{ color: 'var(--accent-blue)', fontSize: 11, minWidth: 60, textAlign: 'right' }}>{aside}</span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
