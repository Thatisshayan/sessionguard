/**
 * src/pages/SessionDetail.tsx
 * ----------------------------
 * Full session deep-dive. All data from real API.
 * Real event timeline chart (balance curve + win markers).
 * Behavior analysis panel.
 * Review queue actions.
 * Export center with download.
 * Live session controls.
 *
 * Maturity: Working Prototype
 */

import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, ReferenceLine, ScatterChart, Scatter,
  BarChart, Bar, Cell,
} from 'recharts'
import {
  getSession, getInsights, getAlerts, getReviewQueue,
  getSessionEvents, getEventsSummary, getSessionBehavior,
  acknowledgeAlert, resolveReviewItem, createExport, getExports,
  startLiveRun, getLiveRun, stopLiveRun,
} from '../services/api'
import { AiAnalysisPanel } from '../components/AiAnalysisPanel'
import type {
  Session, Insight, Alert, ReviewItem,
  SessionEvent, EventSummary, BehaviorResult, LiveRun,
} from '../services/api'

// ── Helpers ───────────────────────────────────────────────────────────────────
const money  = (n: number | undefined) => n != null ? `${n >= 0 ? '+' : ''}$${Math.abs(n).toFixed(2)}` : '—'
const pct    = (n: number | undefined) => n != null ? `${n.toFixed(1)}%` : '—'
const col    = (n: number) => n >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
const sevCol: Record<string, string> = {
  critical: 'var(--severity-critical)',
  warning:  'var(--severity-warning)',
  info:     'var(--accent-blue)',
  high:     'var(--severity-critical)',
  moderate: 'var(--severity-warning)',
  low:      'var(--accent-green)',
}

function KPI({ label, value, accent, mono = true }: {
  label: string; value: string; accent?: string; mono?: boolean
}) {
  return (
    <div className="card" style={{ flex: 1, minWidth: 120 }}>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: accent ?? 'var(--text-primary)', fontFamily: mono ? 'var(--font-mono)' : undefined, lineHeight: 1 }}>{value}</div>
    </div>
  )
}

function SevBadge({ sev }: { sev: string }) {
  return <span className={`badge badge-${sev}`}>{sev}</span>
}

// ── Custom tooltip for event chart ────────────────────────────────────────────
function EventTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload as SessionEvent
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Spin #{d.spin_number}</div>
      <div style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginBottom: 2 }}>Balance: ${d.balance_after?.toFixed(2)}</div>
      <div style={{ color: d.win_amount > 0 ? 'var(--accent-green)' : 'var(--text-muted)' }}>
        Win: ${d.win_amount?.toFixed(2)} | Bet: ${d.bet_amount?.toFixed(2)}
      </div>
      <div style={{ color: d.confidence_score < 0.8 ? 'var(--severity-warning)' : 'var(--text-muted)', marginTop: 4 }}>
        Confidence: {(d.confidence_score * 100).toFixed(0)}% · {d.source}
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
export default function SessionDetail() {
  const { id }    = useParams<{ id: string }>()
  const navigate  = useNavigate()
  const sessionId = Number(id)

  const [session,   setSession]   = useState<Session | null>(null)
  const [events,    setEvents]    = useState<SessionEvent[]>([])
  const [evSummary, setEvSummary] = useState<EventSummary | null>(null)
  const [insights,  setInsights]  = useState<Insight[]>([])
  const [alerts_,   setAlerts]    = useState<Alert[]>([])
  const [queue,     setQueue]     = useState<ReviewItem[]>([])
  const [behavior,  setBehavior]  = useState<BehaviorResult | null>(null)
  const [exports_,  setExports]   = useState<any[]>([])
  const [liveRun,   setLiveRun]   = useState<LiveRun | null>(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState('')
  const [exporting, setExporting] = useState('')
  const [activeTab, setActiveTab] = useState<'overview'|'events'|'behavior'|'review'|'exports'|'ai'>('overview')

  const fetchAll = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [s, ins, al, rq, ev, evs, beh, ex] = await Promise.all([
        getSession(sessionId),
        getInsights(sessionId),
        getAlerts({ session_id: sessionId }),
        getReviewQueue({ session_id: sessionId, status: 'pending' }),
        getSessionEvents(sessionId),
        getEventsSummary(sessionId),
        getSessionBehavior(sessionId).catch(() => null),
        getExports(sessionId),
      ])
      setSession(s); setInsights(ins); setAlerts(al); setQueue(rq)
      setEvents(ev.events); setEvSummary(evs); setBehavior(beh)
      setExports(ex)
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load session.')
    } finally { setLoading(false) }
  }, [sessionId])

  useEffect(() => { fetchAll() }, [fetchAll])

  const handleExport = async (fmt: string) => {
    setExporting(fmt)
    try {
      const r = await createExport(fmt, sessionId)
      const ex = await getExports(sessionId)
      setExports(ex)
      // Trigger download if file_path is available
      if (r.export_id) {
        window.open(`http://127.0.0.1:8000/exports/${r.export_id}/download`, '_blank')
      }
    } finally { setExporting('') }
  }

  const handleAck    = async (id: number) => { await acknowledgeAlert(id); setAlerts(p => p.filter(a => a.id !== id)) }
  const handleResolve = async (id: number, action: string) => {
    await resolveReviewItem(id, action); setQueue(p => p.filter(r => r.id !== id))
  }

  const handleStartLive = async () => {
    const r = await startLiveRun(sessionId, 'mock', 2.0)
    const run = await getLiveRun(r.run_id)
    setLiveRun(run)
  }

  const handleStopLive = async () => {
    if (liveRun) { await stopLiveRun(liveRun.id); setLiveRun(null) }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
      Loading session…
    </div>
  )

  if (error || !session) return (
    <div style={{ padding: 'var(--page-margin)' }}>
      <div className="card" style={{ borderColor: 'var(--severity-critical)', maxWidth: 500 }}>
        <div style={{ color: 'var(--severity-critical)', fontWeight: 600, marginBottom: 8 }}>Failed to load session</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{error}</div>
        <button onClick={() => navigate('/sessions')} style={{ marginTop: 12, background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>← Sessions</button>
      </div>
    </div>
  )

  const rtpColor    = session.rtp < 85 ? 'var(--severity-critical)' : session.rtp < 96 ? 'var(--severity-warning)' : 'var(--accent-blue)'
  const streakColor = session.losing_streak > 15 ? 'var(--severity-critical)' : session.losing_streak > 8 ? 'var(--severity-warning)' : 'var(--text-primary)'
  const unackedAlerts = alerts_.filter(a => !a.acknowledged)

  // Chart data — sample events if too many
  const chartData = events.length > 200 ? events.filter((_, i) => i % Math.ceil(events.length / 200) === 0) : events

  const TAB_BTN = (key: typeof activeTab, label: string, count?: number) => (
    <button key={key} onClick={() => setActiveTab(key)}
      style={{
        background: activeTab === key ? 'var(--accent-blue)' : 'var(--bg-elevated)',
        border: `1px solid ${activeTab === key ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
        color: activeTab === key ? '#fff' : 'var(--text-secondary)',
        padding: '6px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 500,
      }}>
      {label}{count != null && count > 0 ? ` (${count})` : ''}
    </button>
  )

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 'var(--content-max-width)', margin: '0 auto' }}>

      {/* ── Breadcrumb ───────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 'var(--space-4)', fontSize: 13 }}>
        <button onClick={() => navigate('/sessions')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}>← Sessions</button>
        <span style={{ color: 'var(--bg-border)' }}>/</span>
        <span style={{ color: 'var(--text-secondary)' }}>{session.name}</span>
      </div>

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-6)' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>{session.name}</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            {session.game_name} · {session.platform} · {session.date} · {session.duration_minutes} min
            {events.length > 0 && <span style={{ marginLeft: 12, color: 'var(--accent-blue)' }}>{events.length} events</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {liveRun ? (
            <button onClick={handleStopLive} style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid var(--severity-critical)', color: 'var(--severity-critical)', padding: '7px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              ⏹ Stop Live
            </button>
          ) : (
            <button onClick={handleStartLive} style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', padding: '7px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              ▶ Start Live
            </button>
          )}
          <span className={`badge badge-${session.status === 'flagged' ? 'warning' : 'success'}`}>{session.status}</span>
        </div>
      </div>

      {/* ── KPI strip ────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 'var(--gutter)', marginBottom: 'var(--space-6)', flexWrap: 'wrap' }}>
        <KPI label="Net Result"     value={money(session.net_result)}      accent={col(session.net_result)} />
        <KPI label="RTP"            value={pct(session.rtp)}               accent={rtpColor} />
        <KPI label="Spins"          value={session.spins.toLocaleString()} />
        <KPI label="Total Wagered"  value={`$${session.total_bets.toFixed(2)}`} />
        <KPI label="Total Returned" value={`$${session.total_wins.toFixed(2)}`} />
        <KPI label="Biggest Win"    value={`$${session.biggest_win.toFixed(2)}`} accent="var(--accent-green)" />
        <KPI label="Losing Streak"  value={`${session.losing_streak}`}         accent={streakColor} />
        {evSummary && <KPI label="Win Rate"    value={`${evSummary.win_rate_pct}%`} />}
        {evSummary && <KPI label="Avg Bet"     value={`$${evSummary.avg_bet}`} />}
        {behavior   && <KPI label="Risk Score" value={`${behavior.risk_score}/100`} accent={sevCol[behavior.risk_level] ?? 'var(--text-primary)'} />}
      </div>

      {/* ── Tab bar ──────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-6)' }}>
        {TAB_BTN('overview',  'Overview')}
        {TAB_BTN('events',    'Event Timeline', events.length)}
        {TAB_BTN('behavior',  'Behavior')}
        {TAB_BTN('review',    'Review Queue', queue.length)}
        {TAB_BTN('exports',   'Exports')}{TAB_BTN('ai', 'AI Analysis 🤖')}
      </div>

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* TAB: OVERVIEW                                                       */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'overview' && (
        <>
          {/* Balance chart */}
          {chartData.length > 0 && (
            <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
                Balance Curve ({chartData.length} points{events.length > 200 ? ' — sampled' : ''})
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="var(--accent-blue)" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" />
                  <XAxis dataKey="spin_number" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} label={{ value: 'Spin #', fill: 'var(--text-muted)', fontSize: 10, position: 'insideBottomRight', offset: -10 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
                  <Tooltip content={<EventTooltip />} />
                  <ReferenceLine y={session.start_balance} stroke="var(--text-muted)" strokeDasharray="4 4" label={{ value: 'Start', fill: 'var(--text-muted)', fontSize: 10 }} />
                  <Area type="monotone" dataKey="balance_after" stroke="var(--accent-blue)" fill="url(#balGrad)" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: 'var(--accent-blue)' }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Insights + Alerts grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gutter)' }}>
            <div className="card">
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
                Intelligence Insights ({insights.length})
              </div>
              {insights.length === 0
                ? <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No insights yet.</div>
                : insights.map(ins => (
                  <div key={ins.id} style={{ marginBottom: 'var(--space-3)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--bg-border)' }}>
                    <div style={{ marginBottom: 4 }}><SevBadge sev={ins.severity} /></div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{ins.text}</div>
                  </div>
                ))
              }
            </div>
            <div className="card">
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
                Alerts ({unackedAlerts.length} active)
              </div>
              {unackedAlerts.length === 0
                ? <div style={{ color: 'var(--accent-green)', fontSize: 13 }}>✓ No active alerts.</div>
                : unackedAlerts.map(al => (
                  <div key={al.id} style={{ marginBottom: 'var(--space-3)', paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--bg-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <SevBadge sev={al.severity} />
                      <button onClick={() => handleAck(al.id)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 11 }}>Dismiss ×</button>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{al.message}</div>
                  </div>
                ))
              }
            </div>
          </div>
        </>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* TAB: EVENT TIMELINE                                                 */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'events' && (
        <>
          {evSummary && (
            <div style={{ display: 'flex', gap: 'var(--gutter)', marginBottom: 'var(--space-6)', flexWrap: 'wrap' }}>
              <KPI label="Total Events"   value={String(evSummary.total_events)} />
              <KPI label="Winning Spins"  value={String(evSummary.winning_spins)} accent="var(--accent-green)" />
              <KPI label="Losing Spins"   value={String(evSummary.losing_spins)}  accent="var(--accent-red)" />
              <KPI label="Win Rate"       value={`${evSummary.win_rate_pct}%`} />
              <KPI label="Avg Bet"        value={`$${evSummary.avg_bet}`} />
              <KPI label="Biggest Win"    value={`$${evSummary.biggest_win}`} accent="var(--accent-green)" />
              <KPI label="Avg Confidence" value={`${((evSummary.avg_confidence ?? 0) * 100).toFixed(0)}%`} accent={evSummary.avg_confidence < 0.8 ? 'var(--severity-warning)' : undefined} />
              <KPI label="Low Conf"       value={String(evSummary.low_conf_count)} accent={evSummary.low_conf_count > 5 ? 'var(--severity-warning)' : undefined} />
            </div>
          )}

          {/* Win distribution bar chart */}
          {events.length > 0 && (() => {
            const wins    = events.filter(e => e.win_amount > 0)
            const buckets = [0, 1, 2, 5, 10, 25, 50, 999]
            const data    = buckets.slice(0, -1).map((low, i) => ({
              range:  `$${low}–${buckets[i+1]}`,
              count:  wins.filter(e => e.win_amount >= low && e.win_amount < buckets[i+1]).length,
            })).filter(d => d.count > 0)

            return (
              <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>Win Distribution</div>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" />
                    <XAxis dataKey="range" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="count" fill="var(--accent-green)" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )
          })()}

          {/* Event table */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--bg-border)', fontSize: 13, fontWeight: 600 }}>
              Events ({events.length})
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--bg-border)', background: 'var(--bg-elevated)' }}>
                    {['#', 'Timestamp', 'Type', 'Bet', 'Win', 'Balance', 'Confidence', 'Source'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {events.slice(0, 200).map(ev => (
                    <tr key={ev.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                      <td style={{ padding: '7px 12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{ev.spin_number}</td>
                      <td style={{ padding: '7px 12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 10 }}>{ev.timestamp?.slice(0,19)}</td>
                      <td style={{ padding: '7px 12px' }}><span className="badge badge-info" style={{ fontSize: 9 }}>{ev.event_type}</span></td>
                      <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>${ev.bet_amount?.toFixed(2)}</td>
                      <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: ev.win_amount > 0 ? 'var(--accent-green)' : 'var(--text-muted)', fontWeight: ev.win_amount > 0 ? 700 : 400 }}>
                        {ev.win_amount > 0 ? `$${ev.win_amount.toFixed(2)}` : '—'}
                      </td>
                      <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>${ev.balance_after?.toFixed(2)}</td>
                      <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: ev.confidence_score < 0.8 ? 'var(--severity-warning)' : 'var(--text-muted)', fontSize: 11 }}>
                        {(ev.confidence_score * 100).toFixed(0)}%
                      </td>
                      <td style={{ padding: '7px 12px', color: 'var(--text-muted)', fontSize: 11 }}>{ev.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {events.length > 200 && (
                <div style={{ padding: '10px 16px', color: 'var(--text-muted)', fontSize: 12, borderTop: '1px solid var(--bg-border)' }}>
                  Showing 200 of {events.length} events. Export to Excel for the full dataset.
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* TAB: BEHAVIOR                                                        */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'behavior' && (
        <>
          {!behavior ? (
            <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              Behavior analysis unavailable — need at least 3 events.
            </div>
          ) : (
            <>
              {/* Risk score */}
              <div className="card" style={{ marginBottom: 'var(--space-6)', borderColor: sevCol[behavior.risk_level] ?? 'var(--bg-border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>Behavior Risk Assessment</div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 700, color: sevCol[behavior.risk_level] }}>
                    {behavior.risk_score}<span style={{ fontSize: 13, color: 'var(--text-muted)' }}>/100</span>
                  </span>
                </div>
                <div style={{ background: 'var(--bg-base)', borderRadius: 4, height: 6, marginBottom: 12 }}>
                  <div style={{ background: sevCol[behavior.risk_level], height: '100%', borderRadius: 4, width: `${behavior.risk_score}%`, transition: 'width 0.5s ease' }} />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{behavior.summary}</div>
              </div>

              {/* Pattern cards */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gutter)', marginBottom: 'var(--space-6)' }}>
                {Object.entries(behavior.patterns).map(([key, pattern]) => (
                  <div key={key} className="card" style={{ borderColor: pattern.detected ? (sevCol[pattern.severity] ?? 'var(--bg-border)') : 'var(--bg-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                        {key.replace(/_/g, ' ')}
                      </div>
                      {pattern.detected
                        ? <SevBadge sev={pattern.severity} />
                        : <span className="badge badge-success">clear</span>
                      }
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{pattern.detail}</div>
                    {/* Extra metrics per pattern */}
                    {pattern.slope != null && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
                        slope={pattern.slope} {pattern.escalation_ratio != null && `| ratio=${pattern.escalation_ratio}x`}
                      </div>
                    )}
                    {pattern.max_streak != null && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
                        max streak={pattern.max_streak} | clusters={pattern.clusters?.length ?? 0}
                      </div>
                    )}
                    {pattern.peak_volatility != null && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
                        peak vol=${pattern.peak_volatility} | zones={pattern.zones?.length ?? 0}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {behavior.findings.length > 0 && (
                <div className="card">
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Key Findings</div>
                  {behavior.findings.map((f, i) => (
                    <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '8px 0', borderBottom: '1px solid var(--bg-border)', lineHeight: 1.6 }}>
                      ▶ {f}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* TAB: REVIEW QUEUE                                                    */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'review' && (
        <div>
          {queue.length === 0 ? (
            <div className="card" style={{ color: 'var(--accent-green)' }}>✓ Review queue is clear for this session.</div>
          ) : (
            queue.map(item => (
              <div key={item.id} className="card" style={{ marginBottom: 'var(--space-4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: 12, marginBottom: 8, fontSize: 12, color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                      <span>Confidence: <span style={{ fontFamily: 'var(--font-mono)', color: (item.confidence_score ?? 1) < 0.75 ? 'var(--severity-warning)' : 'var(--text-secondary)' }}>
                        {((item.confidence_score ?? 0) * 100).toFixed(0)}%
                      </span></span>
                      {item.bet_amount != null && <span>Bet: ${item.bet_amount.toFixed(2)}</span>}
                      {item.win_amount != null && <span>Win: ${item.win_amount.toFixed(2)}</span>}
                      {item.event_timestamp && <span>{item.event_timestamp.slice(0, 19)}</span>}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item.reason}</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginLeft: 16 }}>
                    <button onClick={() => handleResolve(item.id, 'accepted')}
                      style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12 }}>
                      ✓ Accept
                    </button>
                    <button onClick={() => handleResolve(item.id, 'rejected')}
                      style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12 }}>
                      ✗ Reject
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}


      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* TAB: AI ANALYSIS (V13 — Claude-powered)                             */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'ai' && (
        <AiAnalysisPanel sessionId={sessionId} />
      )}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {/* TAB: EXPORTS                                                         */}
      {/* ════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'exports' && (
        <div>
          <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Generate Export</div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {[
                { fmt: 'pdf',   label: 'PDF Report',     icon: '📄' },
                { fmt: 'excel', label: 'Excel Workbook',  icon: '📊' },
                { fmt: 'json',  label: 'JSON Data',       icon: '{}' },
                { fmt: 'csv',   label: 'CSV Export',      icon: '≡'  },
              ].map(({ fmt, label, icon }) => (
                <button key={fmt} onClick={() => handleExport(fmt)} disabled={!!exporting}
                  style={{
                    background: exporting === fmt ? 'var(--accent-blue)' : 'var(--bg-elevated)',
                    border: `1px solid ${exporting === fmt ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
                    color: exporting === fmt ? '#fff' : 'var(--text-primary)',
                    padding: '12px 20px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
                    fontSize: 13, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8,
                  }}>
                  <span style={{ fontSize: 18 }}>{icon}</span>
                  {exporting === fmt ? 'Generating…' : label}
                </button>
              ))}
            </div>
          </div>

          <div className="card">
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Export History</div>
            {exports_.length === 0
              ? <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No exports for this session yet.</div>
              : exports_.map((ex: any) => (
                <div key={ex.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--bg-border)' }}>
                  <div>
                    <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{ex.file_path?.split('/').pop()}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{ex.created_at?.slice(0, 16)}</div>
                  </div>
                  <button
                    onClick={() => window.open(`http://127.0.0.1:8000/exports/${ex.id}/download`, '_blank')}
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12 }}>
                    ↓ Download
                  </button>
                </div>
              ))
            }
          </div>
        </div>
      )}
    </div>
  )
}
