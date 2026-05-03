/**
 * src/pages/JobsMonitor.tsx
 * --------------------------
 * Background job queue monitor.
 * Shows running, pending, complete, error jobs with live progress.
 * Maturity: Working Prototype
 */

import { useEffect, useState, useRef } from 'react'
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  complete:  { color: 'var(--accent-green)' },
  error:     { color: 'var(--severity-critical)' },
  running:   { color: 'var(--accent-blue)' },
  pending:   { color: 'var(--text-muted)' },
  cancelled: { color: 'var(--text-muted)' },
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div style={{ background: 'var(--bg-base)', borderRadius: 3, height: 4, width: 100 }}>
      <div style={{ background: 'var(--accent-blue)', height: '100%', borderRadius: 3, width: `${pct}%`, transition: 'width 0.3s ease' }} />
    </div>
  )
}

export default function JobsMonitor() {
  const [jobs,   setJobs]   = useState<any[]>([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchJobs = async () => {
    try {
      const params = filter !== 'all' ? `?status=${filter}` : ''
      const res = await axios.get(`${BASE}/jobs${params}&limit=100`)
      setJobs(res.data)
    } catch { /* no-op */ }
    finally { setLoading(false) }
  }

  useEffect(() => {
    fetchJobs()
    pollRef.current = setInterval(fetchJobs, 3000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [filter])

  const cancelJob = async (id: number) => {
    await axios.post(`${BASE}/jobs/${id}/cancel`)
    await fetchJobs()
  }

  const filteredJobs = jobs

  const FILTERS = ['all', 'pending', 'running', 'complete', 'error', 'cancelled']
  const counts: Record<string, number> = {}
  jobs.forEach(j => { counts[j.status] = (counts[j.status] ?? 0) + 1 })
  counts['all'] = jobs.length

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 1000 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-8)' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Job Queue</h1>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Background jobs — CSV parsing, video pipeline, exports, regeneration
          </div>
        </div>
        <button onClick={fetchJobs} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '7px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>
          ↻ Refresh
        </button>
      </div>

      {/* Status filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-6)', flexWrap: 'wrap' }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            style={{
              background: filter === f ? 'var(--accent-blue)' : 'var(--bg-elevated)',
              border: `1px solid ${filter === f ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
              color: filter === f ? '#fff' : 'var(--text-secondary)',
              padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12,
            }}>
            {f.charAt(0).toUpperCase() + f.slice(1)} {counts[f] != null ? `(${counts[f]})` : ''}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
      ) : filteredJobs.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>⚙</div>
          No {filter !== 'all' ? filter : ''} jobs found.
          <div style={{ fontSize: 12, marginTop: 8 }}>Jobs are created automatically when you upload files or trigger exports.</div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-border)', background: 'var(--bg-elevated)' }}>
                {['ID', 'Type', 'Status', 'Progress', 'Session', 'Started', 'Duration', ''].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredJobs.map(j => {
                const startMs   = j.started_at   ? new Date(j.started_at).getTime()   : null
                const endMs     = j.completed_at ? new Date(j.completed_at).getTime() : null
                const duration  = startMs && endMs ? `${((endMs - startMs) / 1000).toFixed(1)}s` : startMs ? 'Running…' : '—'
                const resultStr = typeof j.result === 'object' ? JSON.stringify(j.result) : j.result

                return (
                  <tr key={j.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 11 }}>#{j.id}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="badge badge-info" style={{ fontSize: 10 }}>{j.job_type}</span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ ...(STATUS_STYLE[j.status] ?? {}), fontWeight: 600, fontSize: 12 }}>
                        {j.status === 'running' ? '⚙ ' : j.status === 'complete' ? '✓ ' : j.status === 'error' ? '✗ ' : ''}
                        {j.status}
                      </span>
                      {j.error_message && <div style={{ fontSize: 11, color: 'var(--severity-critical)', marginTop: 3, maxWidth: 200 }}>{j.error_message.slice(0,60)}</div>}
                      {resultStr && j.status === 'complete' && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3, fontFamily: 'var(--font-mono)' }}>{resultStr.slice(0,50)}</div>}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <ProgressBar pct={j.progress ?? 0} />
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{j.progress ?? 0}%</div>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 12 }}>
                      {j.session_id ? `#${j.session_id}` : '—'}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 10 }}>
                      {j.started_at?.slice(11,19) ?? j.created_at?.slice(11,19)}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontSize: 12 }}>
                      {duration}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      {j.status === 'pending' && (
                        <button onClick={() => cancelJob(j.id)}
                          style={{ background: 'none', border: '1px solid var(--bg-border)', color: 'var(--text-muted)', padding: '4px 10px', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Info */}
      <div className="card" style={{ marginTop: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Job Types</div>
        {[
          ['video_pipeline', 'FFmpeg frame extraction + OCR pass + event building — triggered on video upload'],
          ['csv_parse',      'Parse uploaded CSV into sessions and events — triggered on CSV upload'],
          ['export_pdf',     'Generate PDF report — triggered from Reports or Session Detail'],
          ['export_excel',   'Generate Excel workbook — triggered from Reports or Session Detail'],
          ['regenerate',     'Re-run insights and alerts for a session — triggered manually or after data update'],
        ].map(([type, desc]) => (
          <div key={type} style={{ padding: '8px 0', borderBottom: '1px solid var(--bg-border)', display: 'flex', gap: 16, fontSize: 12 }}>
            <span className="badge badge-info" style={{ flexShrink: 0, fontSize: 10, alignSelf: 'flex-start', marginTop: 2 }}>{type}</span>
            <span style={{ color: 'var(--text-secondary)' }}>{desc}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
