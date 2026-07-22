/**
 * src/components/session-detail/ReviewTab.tsx
 * -------------------------------------------------
 * Per-session review queue: accept/reject low-confidence OCR events.
 */

export function ReviewTab({ queue, onResolve }: {
  queue: any[]
  onResolve: (id: number, action: string) => void
}) {
  if (queue.length === 0) {
    return <div className="card" style={{ color: 'var(--accent-green)' }}>✓ Review queue is clear for this session.</div>
  }

  return (
    <div>
      {queue.map(item => (
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
              <button onClick={() => onResolve(item.id, 'accepted')}
                style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12 }}>
                ✓ Accept
              </button>
              <button onClick={() => onResolve(item.id, 'rejected')}
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12 }}>
                ✗ Reject
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
