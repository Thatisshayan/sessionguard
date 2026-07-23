/**
 * src/pages/JobsMonitor.tsx
 * --------------------------
 * Background job queue monitor — real-time via WebSocket.
 * Shows running, pending, complete, error jobs with live progress.
 */

import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useJobWebSocket } from '../hooks/useJobWebSocket'
import { getJobs, cancelJobApi, Job } from '../services/api'
import { toast } from '../components/Toast'

const STATUS_STYLE: Record<string, string> = {
  complete: 'var(--accent-green)',
  error: 'var(--severity-critical)',
  running: 'var(--accent-blue)',
  pending: 'var(--text-muted)',
  cancelled: 'var(--text-muted)',
}

const STAGE_LABEL: Record<string, string> = {
  extracting_frames: 'Extracting frames…',
  ocr_pass: 'Running OCR…',
  building_events: 'Building events…',
  validation: 'Validating events…',
  done: 'Complete',
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div style={{ background: 'var(--bg-base)', borderRadius: 3, height: 4, width: 100 }}>
      <div style={{ background: 'var(--accent-blue)', height: '100%', borderRadius: 3, width: `${pct}%`, transition: 'width 0.3s ease' }} />
    </div>
  )
}

export default function JobsMonitor() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState('all')
  const [liveProgress, setLiveProgress] = useState<Record<number, { progress: number; stage: string }>>({})

  const jobsQ = useQuery({
    queryKey: ['jobs', filter],
    queryFn: () => getJobs({ status: filter !== 'all' ? filter : undefined, limit: 100 }),
    refetchInterval: false,
  })
  const jobs: Job[] = jobsQ.data ?? []

  const cancelM = useMutation({
    mutationFn: (id: number) => cancelJobApi(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['jobs'] }); toast.success('Job cancelled') },
    onError: () => { toast.error('Failed to cancel job') },
  })

  const handleProgress = useCallback((data: { job_id: number; progress: number; stage: string }) => {
    setLiveProgress(prev => ({ ...prev, [data.job_id]: { progress: data.progress, stage: data.stage } }))
  }, [])

  const handleComplete = useCallback(() => {
    qc.invalidateQueries({ queryKey: ['jobs'] })
  }, [qc])

  const { connected } = useJobWebSocket(handleProgress, handleComplete)

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
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            fontSize: 11, padding: '3px 8px', borderRadius: 4,
            background: connected ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
            color: connected ? 'var(--accent-green)' : 'var(--severity-critical)',
          }}>
            {connected ? '● Live' : '○ Disconnected'}
          </span>
          <button onClick={() => jobsQ.refetch()} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '7px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>
            ↻ Refresh
          </button>
        </div>
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

      {jobsQ.isPending ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
      ) : jobs.length === 0 ? (
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
              {jobs.map(j => {
                const live = liveProgress[j.id]
                const progress = live?.progress ?? j.progress ?? 0
                const stage = live?.stage ?? ''
                const startMs = j.started_at ? new Date(j.started_at).getTime() : null
                const endMs = j.completed_at ? new Date(j.completed_at).getTime() : null
                const duration = startMs && endMs ? `${((endMs - startMs) / 1000).toFixed(1)}s` : startMs ? 'Running…' : '—'
                const resultStr = typeof j.result === 'object' ? JSON.stringify(j.result) : j.result

                return (
                  <tr key={j.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 11 }}>#{j.id}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="badge badge-info" style={{ fontSize: 10 }}>{j.job_type}</span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: STATUS_STYLE[j.status] ?? 'var(--text-secondary)', fontWeight: 600, fontSize: 12 }}>
                        {j.status === 'running' ? '⚙ ' : j.status === 'complete' ? '✓ ' : j.status === 'error' ? '✗ ' : ''}
                        {j.status}
                      </span>
                      {j.error_message && <div style={{ fontSize: 11, color: 'var(--severity-critical)', marginTop: 3, maxWidth: 200 }}>{j.error_message.slice(0,60)}</div>}
                      {resultStr && j.status === 'complete' && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3, fontFamily: 'var(--font-mono)' }}>{resultStr.slice(0,50)}</div>}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      {j.status === 'running' && (
                        <>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>
                            {STAGE_LABEL[stage] || stage} — {progress}%
                          </div>
                          <ProgressBar pct={progress} />
                        </>
                      )}
                      {j.status !== 'running' && (
                        <>
                          <ProgressBar pct={progress} />
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{progress}%</div>
                        </>
                      )}
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
                      {(j.status === 'pending' || j.status === 'running') && (
                        <button onClick={() => cancelM.mutate(j.id)}
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
