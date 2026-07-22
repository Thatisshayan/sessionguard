/**
 * src/components/session-detail/shared.tsx
 * -------------------------------------------
 * Formatting helpers + small presentational atoms shared across the
 * SessionDetail tab components.
 */

export const money = (n: number | undefined) => n != null ? `${n >= 0 ? '+' : ''}$${Math.abs(n).toFixed(2)}` : '—'
export const pct   = (n: number | undefined) => n != null ? `${n.toFixed(1)}%` : '—'
export const col   = (n: number) => n >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'

export const sevCol: Record<string, string> = {
  critical: 'var(--severity-critical)',
  warning:  'var(--severity-warning)',
  info:     'var(--accent-blue)',
  high:     'var(--severity-critical)',
  moderate: 'var(--severity-warning)',
  low:      'var(--accent-green)',
}

export function KPI({ label, value, accent, mono = true }: {
  label: string; value: string; accent?: string; mono?: boolean
}) {
  return (
    <div className="card" style={{ flex: 1, minWidth: 120 }}>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: accent ?? 'var(--text-primary)', fontFamily: mono ? 'var(--font-mono)' : undefined, lineHeight: 1 }}>{value}</div>
    </div>
  )
}

export function SevBadge({ sev }: { sev: string }) {
  return <span className={`badge badge-${sev}`}>{sev}</span>
}

// ── Custom tooltip for event chart ────────────────────────────────────────────
export function EventTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
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
