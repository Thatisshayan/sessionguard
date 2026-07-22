/**
 * src/components/session-detail/EventsTab.tsx
 * -------------------------------------------------
 * Event summary KPIs + win distribution chart + raw event table.
 */

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
} from 'recharts'
import { KPI } from './shared'

export function EventsTab({ events, evSummary }: { events: any[]; evSummary: any }) {
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
          {events.length > 200 && (
            <div style={{ padding: '10px 16px', color: 'var(--text-muted)', fontSize: 12, borderTop: '1px solid var(--bg-border)' }}>
              Showing 200 of {events.length} events. Export to Excel for the full dataset.
            </div>
          )}
        </div>
      </div>
    </>
  )
}
