/**
 * src/components/session-detail/OverviewTab.tsx
 * -------------------------------------------------
 * Balance curve chart + insights/alerts summary grid.
 * Each alert can request an AI-generated (or rule-based fallback) root
 * cause explanation, shown inline once fetched.
 */

import { useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { EventTooltip, SevBadge } from './shared'

export function OverviewTab({ session, events, insights, alerts, onAck, onExplain, explainingAlertId }: {
  session: any
  events: any[]
  insights: any[]
  alerts: any[]
  onAck: (id: number) => void
  onExplain: (id: number) => Promise<any>
  explainingAlertId: number | null
}) {
  const chartData = events.length > 200 ? events.filter((_, i) => i % Math.ceil(events.length / 200) === 0) : events
  const unackedAlerts = alerts.filter(a => !a.acknowledged)
  const [explanations, setExplanations] = useState<Record<number, any>>({})

  const handleExplain = async (alertId: number) => {
    try {
      const result = await onExplain(alertId)
      setExplanations(prev => ({ ...prev, [alertId]: result }))
    } catch { /* toast handled in the mutation */ }
  }

  return (
    <>
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
                  <div style={{ display: 'flex', gap: 10 }}>
                    <button onClick={() => handleExplain(al.id)} disabled={explainingAlertId === al.id}
                      style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer', fontSize: 11 }}>
                      {explainingAlertId === al.id ? 'Explaining…' : (explanations[al.id] ? 'Re-explain' : '? Explain')}
                    </button>
                    <button onClick={() => onAck(al.id)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 11 }}>Dismiss ×</button>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{al.message}</div>
                {explanations[al.id] && (
                  <div style={{ marginTop: 8, padding: '10px 12px', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', fontSize: 12 }}>
                    <div style={{ color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', marginBottom: 4 }}>
                      {explanations[al.id].source === 'nvidia_ai' ? '🤖 AI explanation' : explanations[al.id].source === 'ollama' ? '🤖 Ollama explanation' : 'Rule-based explanation'}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{explanations[al.id].explanation?.explanation}</div>
                  </div>
                )}
              </div>
            ))
          }
        </div>
      </div>
    </>
  )
}
