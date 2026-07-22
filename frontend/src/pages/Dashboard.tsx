/**
 * src/pages/Dashboard.tsx — Phase 3 complete.
 * Real KPIs + live charts + behavior risk summary + insights + alerts + review queue.
 */

import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, CartesianGrid,
} from 'recharts'
import {
  getGlobalMetrics, getNetOverTime, getRtpDistribution,
  getInsights, getAlerts, getAlertSummary,
  getReviewQueue, getQueueSummary,
  acknowledgeAlert, resolveReviewItem,
  getGlobalBehavior,
} from '../services/api'

const fmtC  = (n: number) => `${n >= 0 ? '+$' : '-$'}${Math.abs(n).toFixed(2)}`
const col   = (n: number) => n >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
const RISK_COLOR: Record<string, string> = {
  critical: 'var(--severity-critical)',
  high:     'var(--severity-critical)',
  moderate: 'var(--severity-warning)',
  low:      'var(--accent-green)',
  unknown:  'var(--text-muted)',
}

function KpiCard({ label, value, sub, accent, onClick }: {
  label: string; value: string; sub?: string; accent?: string; onClick?: () => void
}) {
  return (
    <div className="card" style={{ flex: 1, minWidth: 130, cursor: onClick ? 'pointer' : undefined }}
      onClick={onClick}>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: accent ?? 'var(--text-primary)', fontFamily: 'var(--font-mono)', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function SevBadge({ sev }: { sev: string }) {
  return <span className={`badge badge-${sev}`}>{sev}</span>
}

const DASH_KEYS = {
  metrics: ['dashboard', 'metrics'],
  netOverTime: ['dashboard', 'net-over-time'],
  rtpDist: ['dashboard', 'rtp-distribution'],
  insights: ['dashboard', 'insights'],
  alerts: ['dashboard', 'alerts'],
  alertSummary: ['dashboard', 'alert-summary'],
  reviewQueue: ['dashboard', 'review-queue'],
  queueSummary: ['dashboard', 'queue-summary'],
  behavior: ['dashboard', 'behavior'],
} as const

export default function Dashboard() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const metricsQ      = useQuery({ queryKey: DASH_KEYS.metrics,      queryFn: getGlobalMetrics })
  const netOverTimeQ  = useQuery({ queryKey: DASH_KEYS.netOverTime,  queryFn: getNetOverTime })
  const rtpDistQ      = useQuery({ queryKey: DASH_KEYS.rtpDist,      queryFn: getRtpDistribution })
  const insightsQ     = useQuery({ queryKey: DASH_KEYS.insights,     queryFn: () => getInsights() })
  const alertsQ       = useQuery({ queryKey: DASH_KEYS.alerts,       queryFn: () => getAlerts({ unacknowledged_only: true }) })
  const alertSummaryQ = useQuery({ queryKey: DASH_KEYS.alertSummary, queryFn: getAlertSummary })
  const reviewQ       = useQuery({ queryKey: DASH_KEYS.reviewQueue,  queryFn: () => getReviewQueue({ status: 'pending' }) })
  const queueSummaryQ = useQuery({ queryKey: DASH_KEYS.queueSummary, queryFn: getQueueSummary })
  const behaviorQ     = useQuery({ queryKey: DASH_KEYS.behavior,     queryFn: getGlobalBehavior, retry: false })

  const metrics      = metricsQ.data ?? null
  const netOverTime   = netOverTimeQ.data ?? []
  const rtpDist       = rtpDistQ.data ?? []
  const insights      = insightsQ.data ?? []
  const alerts_       = alertsQ.data ?? []
  const alertSummary  = alertSummaryQ.data ?? null
  const reviewItems   = reviewQ.data ?? []
  const queueSummary  = queueSummaryQ.data ?? null
  const behaviorData  = behaviorQ.data ?? null

  const coreQueries = [metricsQ, netOverTimeQ, rtpDistQ, insightsQ, alertsQ, alertSummaryQ, reviewQ, queueSummaryQ]
  const loading    = coreQueries.some(q => q.isPending)
  const error      = (coreQueries.find(q => q.error)?.error as any)?.message ?? null
  const lastUpdated = metricsQ.dataUpdatedAt ? new Date(metricsQ.dataUpdatedAt).toLocaleTimeString() : ''

  const fetchAll = () => qc.invalidateQueries({ queryKey: ['dashboard'] })

  const ackMutation = useMutation({
    mutationFn: (id: number) => acknowledgeAlert(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: DASH_KEYS.alerts }),
  })
  const resolveMutation = useMutation({
    mutationFn: ({ id, action }: { id: number; action: string }) => resolveReviewItem(id, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: DASH_KEYS.reviewQueue })
      qc.invalidateQueries({ queryKey: DASH_KEYS.queueSummary })
    },
  })

  const handleAcknowledge = (id: number) => ackMutation.mutate(id)
  const handleResolve = (id: number, action: string) => resolveMutation.mutate({ id, action })

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', gap: 12, flexDirection: 'column' }}>
      <div style={{ fontSize: 32 }}>⏳</div>
      <div>Loading dashboard…</div>
    </div>
  )

  if (error) return (
    <div style={{ padding: 'var(--page-margin)' }}>
      <div className="card" style={{ borderColor: 'var(--severity-critical)', maxWidth: 600 }}>
        <div style={{ color: 'var(--severity-critical)', fontWeight: 600, marginBottom: 8, fontSize: 14 }}>⚠ Backend connection failed</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 12 }}>{error}</div>
        <code style={{ display: 'block', background: 'var(--bg-elevated)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', fontSize: 12, color: 'var(--accent-blue)' }}>
          scripts/run_backend.bat  (Windows)<br/>
          bash scripts/run_backend.sh  (Mac/Linux)
        </code>
        <button onClick={fetchAll} style={{ marginTop: 14, background: 'var(--accent-blue)', border: 'none', color: '#fff', padding: '8px 18px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>
          ↻ Retry
        </button>
      </div>
    </div>
  )

  const criticalInsights  = insights.filter(i => i.severity === 'critical')
  const highRiskSessions  = behaviorData?.sessions?.filter((s: any) => s.risk_flags >= 2) ?? []

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 'var(--content-max-width)', margin: '0 auto' }}>

      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-8)' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Dashboard</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            {metrics?.total_sessions} sessions
            {alertSummary && <> · <span style={{ color: alertSummary.critical > 0 ? 'var(--severity-critical)' : 'var(--text-muted)' }}>{alertSummary.unacknowledged} alerts</span></>}
            {queueSummary && <> · {queueSummary.pending} in queue</>}
            {lastUpdated && <span style={{ marginLeft: 12, color: 'var(--text-muted)', fontSize: 11 }}>Updated {lastUpdated}</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => navigate('/live')}
            style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', padding: '7px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
            ⏱ Live Monitor
          </button>
          <button onClick={fetchAll}
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '7px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* ── KPI strip ───────────────────────────────────────────────────── */}
      {metrics && (
        <div style={{ display: 'flex', gap: 'var(--gutter)', marginBottom: 'var(--space-8)', flexWrap: 'wrap' }}>
          <KpiCard label="Total Net"       value={fmtC(metrics.total_net)}           accent={col(metrics.total_net)} />
          <KpiCard label="Avg RTP"         value={`${metrics.avg_rtp}%`}             sub="across all sessions" />
          <KpiCard label="Sessions"        value={String(metrics.total_sessions)}     onClick={() => navigate('/sessions')} />
          <KpiCard label="Total Spins"     value={metrics.total_spins.toLocaleString()} />
          <KpiCard label="Total Wagered"   value={`$${metrics.total_wagered.toFixed(2)}`} />
          <KpiCard label="Biggest Win"     value={`$${metrics.all_time_biggest_win}`} accent="var(--accent-green)" />
          <KpiCard label="Worst Streak"    value={`${metrics.worst_streak}`}          accent={metrics.worst_streak > 15 ? 'var(--severity-critical)' : undefined} />
          <KpiCard label="Flagged"         value={String(metrics.flagged_count)}      accent={metrics.flagged_count > 0 ? 'var(--severity-warning)' : undefined} onClick={() => navigate('/sessions?status=flagged')} />
        </div>
      )}

      {/* ── Charts row ──────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gutter)', marginBottom: 'var(--space-8)' }}>
        <div className="card">
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', letterSpacing: '0.02em' }}>Cumulative Net Result</div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={netOverTime} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="netGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="var(--accent-blue)" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" />
              <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 11 }}
                formatter={(v: any) => [`$${Number(v).toFixed(2)}`, 'Cumulative Net']} />
              <Area type="monotone" dataKey="cumulative_net" stroke="var(--accent-blue)" fill="url(#netGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)', letterSpacing: '0.02em' }}>RTP Distribution</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={rtpDist} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" />
              <XAxis dataKey="bucket" tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 9 }} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 11 }} />
              <Bar dataKey="count" fill="var(--accent-blue)" radius={[4,4,0,0]} label={{ position: 'top', fill: 'var(--text-muted)', fontSize: 9 }} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Behavior risk banner (if any high-risk sessions) ─────────────── */}
      {behaviorData && behaviorData.high_risk_count > 0 && (
        <div style={{
          marginBottom: 'var(--space-6)',
          padding: '14px 18px',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(239,68,68,0.07)',
          border: '1px solid rgba(239,68,68,0.25)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--severity-critical)', fontSize: 13, marginBottom: 4 }}>
              ⚠ {behaviorData.high_risk_count} high-risk session{behaviorData.high_risk_count > 1 ? 's' : ''} detected
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {highRiskSessions.slice(0,3).map((s: any) => s.session_name).join(' · ')}
              {highRiskSessions.length > 3 && ` + ${highRiskSessions.length - 3} more`}
            </div>
          </div>
          <button onClick={() => navigate('/sessions')}
            style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)', color: 'var(--severity-critical)', padding: '7px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, whiteSpace: 'nowrap' }}>
            Review sessions →
          </button>
        </div>
      )}

      {/* ── Three-panel bottom row ────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--gutter)' }}>

        {/* Insights */}
        <div className="card" style={{ maxHeight: 400, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>Intelligence Insights</div>
            <span style={{ fontSize: 11, color: criticalInsights.length > 0 ? 'var(--severity-critical)' : 'var(--text-muted)' }}>
              {criticalInsights.length} critical
            </span>
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {insights.slice(0, 10).map(ins => (
              <div key={ins.id} style={{ paddingBottom: 'var(--space-3)', marginBottom: 'var(--space-3)', borderBottom: '1px solid var(--bg-border)', cursor: 'pointer' }}
                onClick={() => navigate(`/sessions/${ins.session_id}`)}>
                <div style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                  <SevBadge sev={ins.severity} />
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', alignSelf: 'center' }}>{ins.game_name}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{ins.text}</div>
              </div>
            ))}
            {insights.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No insights yet.</div>}
          </div>
        </div>

        {/* Alerts */}
        <div className="card" style={{ maxHeight: 400, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>Active Alerts</div>
            {alertSummary && (
              <span style={{ fontSize: 11 }}>
                <span style={{ color: alertSummary.critical > 0 ? 'var(--severity-critical)' : 'var(--text-muted)' }}>{alertSummary.critical}C</span>
                {' · '}
                <span style={{ color: alertSummary.warning > 0 ? 'var(--severity-warning)' : 'var(--text-muted)' }}>{alertSummary.warning}W</span>
              </span>
            )}
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {alerts_.slice(0, 8).map(al => (
              <div key={al.id} style={{ paddingBottom: 'var(--space-3)', marginBottom: 'var(--space-3)', borderBottom: '1px solid var(--bg-border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                  <SevBadge sev={al.severity} />
                  <button onClick={() => handleAcknowledge(al.id)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 11, padding: 0, flexShrink: 0 }}>
                    ×
                  </button>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{al.message}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{al.session_name}</div>
              </div>
            ))}
            {alerts_.length === 0 && <div style={{ color: 'var(--accent-green)', fontSize: 12 }}>✓ No active alerts.</div>}
          </div>
        </div>

        {/* Review Queue */}
        <div className="card" style={{ maxHeight: 400, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>Review Queue</div>
            {queueSummary && (
              <span style={{ fontSize: 11, color: queueSummary.pending > 0 ? 'var(--severity-warning)' : 'var(--accent-green)' }}>
                {queueSummary.pending} pending
              </span>
            )}
          </div>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {reviewItems.slice(0, 6).map(item => (
              <div key={item.id} style={{ paddingBottom: 'var(--space-3)', marginBottom: 'var(--space-3)', borderBottom: '1px solid var(--bg-border)' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: (item.confidence_score ?? 1) < 0.75 ? 'var(--severity-warning)' : 'var(--text-secondary)' }}>
                    {((item.confidence_score ?? 0) * 100).toFixed(0)}%
                  </span>
                  {' · '}{item.game_name}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 8 }}>{item.reason}</div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {(['accepted', 'rejected'] as const).map(action => (
                    <button key={action} onClick={() => handleResolve(item.id, action)}
                      style={{
                        background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
                        color: action === 'accepted' ? 'var(--accent-green)' : 'var(--accent-red)',
                        padding: '3px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 10,
                      }}>
                      {action === 'accepted' ? '✓' : '✗'} {action}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {reviewItems.length === 0 && <div style={{ color: 'var(--accent-green)', fontSize: 12 }}>✓ Queue clear.</div>}
            {reviewItems.length > 6 && (
              <button onClick={() => navigate('/review')}
                style={{ width: '100%', background: 'none', border: '1px solid var(--bg-border)', color: 'var(--text-muted)', padding: '6px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 11 }}>
                View all {queueSummary?.pending} items →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
