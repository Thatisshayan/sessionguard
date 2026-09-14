/**
 * src/components/session-detail/EventsTab.tsx
 * -------------------------------------------------
 * Event summary KPIs + win distribution chart + raw event table.
 * Also runs z-score event validation on demand, flagging events whose
 * values look inconsistent (e.g. an OCR misread) with a suggested fix.
 */

import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
} from 'recharts'
import { KPI } from './shared'

interface EventRow {
  id: number; spin_number: number; timestamp: string; event_type: string
  bet_amount: number; win_amount: number; balance_after: number
  confidence_score: number; source: string
}
interface EventsSummary {
  total_events: number; winning_spins: number; losing_spins: number; win_rate_pct: number
  avg_bet: number; biggest_win: number; avg_confidence: number; low_conf_count: number
}

export function EventsTab({ events, evSummary, onValidate, validating, validation }: {
  events: EventRow[]
  evSummary: EventsSummary | undefined
  onValidate: () => void
  validating: boolean
  validation?: {
    total_events: number; valid_events: number; flagged_count: number; auto_corrected: number
    flagged: Array<{ event_id: number; reason: string; severity: string; original_values: Record<string, unknown>; suggested_values: Record<string, unknown> }>
  }
}) {
  const [page, setPage] = useState(1)
  const pageSize = 100
  const visibleEvents = events.slice(0, page * pageSize)

  const wins    = events.filter(e => e.win_amount > 0)
  const buckets = [0, 1, 2, 5, 10, 25, 50, 999]
  const winData = buckets.slice(0, -1).map((low, i) => ({
    range: `$${low}–${buckets[i + 1]}`,
    count: wins.filter(e => e.win_amount >= low && e.win_amount < buckets[i + 1]).length,
  })).filter(d => d.count > 0)

  return (
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

      {events.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Event Validation</div>
            <button onClick={onValidate} disabled={validating} style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)',
              padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12,
            }}>
              {validating ? 'Validating…' : '⟳ Validate Events'}
            </button>
          </div>
          {validation && (
            <>
              <div style={{ display: 'flex', gap: 'var(--gutter)', marginBottom: validation.flagged.length ? 14 : 0, flexWrap: 'wrap' }}>
                <KPI label="Total"          value={String(validation.total_events)} />
                <KPI label="Valid"          value={String(validation.valid_events)} accent="var(--accent-green)" />
                <KPI label="Flagged"        value={String(validation.flagged_count)} accent={validation.flagged_count > 0 ? 'var(--severity-warning)' : undefined} />
                <KPI label="Auto-corrected" value={String(validation.auto_corrected)} />
              </div>
              {validation.flagged.map(f => (
                <div key={f.event_id} style={{ padding: '8px 0', borderTop: '1px solid var(--bg-border)', fontSize: 12 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                    <span className={`badge badge-${f.severity === 'critical' ? 'critical' : 'warning'}`} style={{ fontSize: 9 }}>{f.severity}</span>
                    <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>event #{f.event_id}</span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)' }}>{f.reason}</div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {events.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>Win Distribution</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={winData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--bg-border)" />
              <XAxis dataKey="range" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" fill="var(--accent-green)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--bg-border)', fontSize: 13, fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Events ({events.length})</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Showing {visibleEvents.length} of {events.length}
          </span>
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
              {visibleEvents.map(ev => (
                <tr key={ev.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                  <td style={{ padding: '7px 12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{ev.spin_number}</td>
                  <td style={{ padding: '7px 12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 10 }}>{ev.timestamp?.slice(0, 19)}</td>
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
          {visibleEvents.length < events.length && (
            <div style={{ padding: '12px 16px', textAlign: 'center', borderTop: '1px solid var(--bg-border)', background: 'var(--bg-elevated)' }}>
              <button onClick={() => setPage(p => p + 1)} style={{
                background: 'var(--accent-blue)', color: '#fff', border: 'none',
                padding: '8px 20px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 600
              }}>
                Load More Events ({events.length - visibleEvents.length} remaining)
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
