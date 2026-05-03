/**
 * src/pages/VideoLab.tsx
 * -----------------------
 * Dedicated video analysis workspace.
 * Browse extracted frames, see OCR overlay, review scene changes.
 * Maturity: Working Prototype
 */

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

interface OcrResult {
  id:              number
  frame_path:      string
  balance_value:   number | null
  bet_value:       number | null
  win_value:       number | null
  confidence_avg:  number
  confidence_bal:  number
  confidence_bet:  number
  confidence_win:  number
  flagged:         number
  created_at:      string
}

interface VideoJob {
  id:               number
  status:           string
  frames_extracted: number
  frames_ocr_done:  number
  scene_changes:    number
  events_built:     number
  error_message:    string
  created_at:       string
}

function ConfPill({ value, label }: { value: number; label: string }) {
  const pct   = Math.round((value ?? 0) * 100)
  const color = pct >= 90 ? 'var(--accent-green)' : pct >= 75 ? 'var(--accent-amber)' : 'var(--severity-critical)'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, minWidth: 60 }}>
      <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color }}>{pct}%</div>
      <div style={{ background: 'var(--bg-base)', borderRadius: 3, height: 4, width: 50 }}>
        <div style={{ background: color, height: '100%', borderRadius: 3, width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function VideoLab() {
  const { id }       = useParams<{ id: string }>()
  const sessionId    = Number(id)
  const [jobs,       setJobs]       = useState<VideoJob[]>([])
  const [ocrResults, setOcrResults] = useState<OcrResult[]>([])
  const [selected,   setSelected]   = useState<OcrResult | null>(null)
  const [filter,     setFilter]     = useState<'all' | 'flagged' | 'lowconf'>('all')
  const [loading,    setLoading]    = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get(`${BASE}/video-status`),
      axios.get(`${BASE}/jobs?session_id=${sessionId}&status=complete&limit=10`),
      sessionId ? axios.get(`${BASE}/sessions/${sessionId}/ocr-results`).catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
    ]).then(([, j, ocr]) => {
      setJobs(j.data.filter((x: any) => x.job_type === 'video_pipeline'))
      setOcrResults(ocr.data || [])
    }).finally(() => setLoading(false))
  }, [sessionId])

  const filtered = ocrResults.filter(r => {
    if (filter === 'flagged')  return r.flagged
    if (filter === 'lowconf')  return r.confidence_avg < 0.75
    return true
  })

  const statusColor: Record<string, string> = {
    complete: 'var(--accent-green)',
    running:  'var(--accent-blue)',
    error:    'var(--severity-critical)',
    pending:  'var(--text-muted)',
  }

  if (loading) return (
    <div style={{ padding: 'var(--page-margin)', color: 'var(--text-muted)' }}>Loading Video Lab…</div>
  )

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 1100 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>Video Lab</h1>
      <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 'var(--space-8)' }}>
        Session #{sessionId} — Frame viewer with OCR overlay
      </div>

      {/* Video jobs */}
      {jobs.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Video Pipeline Jobs</div>
          {jobs.map(j => (
            <div key={j.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 12 }}>
              <div>
                <span style={{ color: statusColor[j.status] ?? 'var(--text-muted)', fontWeight: 600 }}>● {j.status}</span>
                <span style={{ color: 'var(--text-muted)', marginLeft: 12 }}>Job #{j.id}</span>
              </div>
              <div style={{ display: 'flex', gap: 20, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                <span>{j.frames_extracted} frames</span>
                <span>{j.frames_ocr_done} OCR'd</span>
                <span>{j.scene_changes} scenes</span>
                <span>{j.events_built} events built</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {ocrResults.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>🎬</div>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8 }}>No frames extracted yet</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
            Upload a video on the Upload page to run the video pipeline.
          </div>
          <button onClick={() => window.location.href = '/upload'}
            style={{ background: 'var(--accent-blue)', border: 'none', color: '#fff', padding: '10px 24px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
            Go to Upload →
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 'var(--gutter)' }}>

          {/* Frame list */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--bg-border)' }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Frames ({filtered.length})</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {(['all','flagged','lowconf'] as const).map(f => (
                  <button key={f} onClick={() => setFilter(f)}
                    style={{
                      flex: 1, padding: '5px 6px', borderRadius: 4, fontSize: 10, cursor: 'pointer',
                      background: filter === f ? 'var(--accent-blue)' : 'var(--bg-elevated)',
                      border: `1px solid ${filter === f ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
                      color: filter === f ? '#fff' : 'var(--text-muted)',
                    }}>
                    {f === 'all' ? 'All' : f === 'flagged' ? 'Flagged' : 'Low conf'}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ maxHeight: 520, overflowY: 'auto' }}>
              {filtered.map((r, i) => (
                <div key={r.id} onClick={() => setSelected(r)}
                  style={{
                    padding: '10px 14px', cursor: 'pointer',
                    background: selected?.id === r.id ? 'var(--bg-elevated)' : 'transparent',
                    borderLeft: selected?.id === r.id ? '3px solid var(--accent-blue)' : '3px solid transparent',
                    borderBottom: '1px solid var(--bg-border)',
                  }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>
                      Frame {i + 1}
                    </span>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {r.flagged ? <span className="badge badge-warning" style={{ fontSize: 8 }}>flagged</span> : null}
                      {r.confidence_avg < 0.75 ? <span className="badge badge-critical" style={{ fontSize: 8 }}>low conf</span> : null}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 11, fontFamily: 'var(--font-mono)' }}>
                    {r.balance_value != null && <span style={{ color: 'var(--accent-blue)' }}>B: ${r.balance_value.toFixed(2)}</span>}
                    {r.bet_value     != null && <span style={{ color: 'var(--accent-amber)' }}>Bet: ${r.bet_value.toFixed(2)}</span>}
                    {r.win_value     != null && r.win_value > 0 && <span style={{ color: 'var(--accent-green)' }}>Win: ${r.win_value.toFixed(2)}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Frame detail */}
          <div>
            {!selected ? (
              <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: 'var(--text-muted)', flexDirection: 'column', gap: 12 }}>
                <div style={{ fontSize: 36 }}>🖼</div>
                <div>Select a frame to inspect</div>
              </div>
            ) : (
              <>
                <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
                    Frame — {selected.frame_path.split('/').pop()}
                    {selected.flagged ? <span className="badge badge-warning" style={{ marginLeft: 8, fontSize: 9 }}>FLAGGED</span> : null}
                  </div>

                  {/* OCR Confidence */}
                  <div style={{ display: 'flex', gap: 24, marginBottom: 16 }}>
                    <ConfPill value={selected.confidence_avg} label="Overall" />
                    <ConfPill value={selected.confidence_bal} label="Balance" />
                    <ConfPill value={selected.confidence_bet} label="Bet" />
                    <ConfPill value={selected.confidence_win} label="Win" />
                  </div>

                  {/* Detected values */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                    {[
                      { label: 'Balance', value: selected.balance_value, color: 'var(--accent-blue)',  conf: selected.confidence_bal },
                      { label: 'Bet',     value: selected.bet_value,     color: 'var(--accent-amber)', conf: selected.confidence_bet },
                      { label: 'Win',     value: selected.win_value,     color: 'var(--accent-green)', conf: selected.confidence_win },
                    ].map(f => (
                      <div key={f.label} style={{ background: 'var(--bg-base)', padding: '12px 14px', borderRadius: 'var(--radius-sm)', border: `1px solid ${f.conf < 0.75 ? 'rgba(245,158,11,0.3)' : 'var(--bg-border)'}` }}>
                        <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>{f.label}</div>
                        <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'var(--font-mono)', color: f.value != null ? f.color : 'var(--text-muted)' }}>
                          {f.value != null ? `$${f.value.toFixed(2)}` : 'Not detected'}
                        </div>
                        {f.conf < 0.75 && f.value != null && (
                          <div style={{ fontSize: 10, color: 'var(--severity-warning)', marginTop: 4 }}>
                            ⚠ Low confidence — needs review
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Tips */}
                {selected.flagged && (
                  <div className="card" style={{ borderColor: 'var(--severity-warning)' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--severity-warning)', marginBottom: 8 }}>⚠ This frame was flagged</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                      One or more fields had confidence below 75%. This frame's values were added to the review queue.
                      Go to the Review Queue tab in Session Detail to accept or reject them.
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                      To improve accuracy: Go to Profiles → Edit the profile for this game → 
                      adjust the ROI coordinates so they target the exact pixel region of each value.
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
