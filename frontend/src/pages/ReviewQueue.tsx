/**
 * src/pages/ReviewQueue.tsx
 * Maturity: Working Prototype — actions wired to real API.
 */
import { useEffect, useState } from 'react'
import { getReviewQueue, getQueueSummary, resolveReviewItem } from '../services/api'
import type { ReviewItem, QueueSummary } from '../services/api'

export default function ReviewQueue() {
  const [items,   setItems]   = useState<ReviewItem[]>([])
  const [summary, setSummary] = useState<QueueSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchAll = () => {
    Promise.all([
      getReviewQueue({ status: 'pending' }),
      getQueueSummary(),
    ]).then(([items, summary]) => { setItems(items); setSummary(summary) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchAll() }, [])

  const resolve = async (id: number, action: string) => {
    await resolveReviewItem(id, action)
    setItems(prev => prev.filter(i => i.id !== id))
    getQueueSummary().then(setSummary)
  }

  return (
    <div style={{ padding: 'var(--page-margin)' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Review Queue</h1>
      {summary && (
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 'var(--space-8)' }}>
          {summary.pending} pending · {summary.accepted} accepted · {summary.rejected} rejected · {summary.corrected} corrected
        </div>
      )}
      {loading ? <p style={{ color: 'var(--text-muted)' }}>Loading…</p> : (
        items.length === 0
          ? <div className="card" style={{ color: 'var(--accent-green)' }}>✓ Review queue is clear.</div>
          : items.map(item => (
            <div key={item.id} className="card" style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', gap: 12, marginBottom: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                    <span>{item.session_name}</span>
                    <span>·</span>
                    <span>Confidence: <span style={{ fontFamily: 'var(--font-mono)', color: (item.confidence_score ?? 1) < 0.75 ? 'var(--severity-warning)' : 'var(--text-secondary)' }}>
                      {((item.confidence_score ?? 0) * 100).toFixed(0)}%
                    </span></span>
                    {item.bet_amount != null && <span>Bet: ${item.bet_amount.toFixed(2)}</span>}
                    {item.win_amount != null && <span>Win: ${item.win_amount.toFixed(2)}</span>}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{item.reason}</div>
                </div>
                <div style={{ display: 'flex', gap: 8, marginLeft: 16 }}>
                  <button onClick={() => resolve(item.id, 'accepted')}
                    style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12 }}>
                    ✓ Accept
                  </button>
                  <button onClick={() => resolve(item.id, 'rejected')}
                    style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12 }}>
                    ✗ Reject
                  </button>
                </div>
              </div>
            </div>
          ))
      )}
    </div>
  )
}
