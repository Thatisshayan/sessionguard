/**
 * src/pages/Upload.tsx
 * Maturity: Working Prototype — file upload, CSV template download, status polling.
 */
import { useState, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadFile, getUploads } from '../services/api'
import { toast } from '../components/Toast'

const FILE_TYPES = 'CSV, MP4, MKV, MOV, AVI, PNG, JPEG'
const ACCEPT     = '.csv,video/mp4,video/x-matroska,video/quicktime,video/x-msvideo,image/png,image/jpeg'

const STATUS_ICON: Record<string, string> = {
  complete:   '✅',
  processing: '⏳',
  error:      '❌',
  pending:    '🕐',
}

const STATUS_COLOR: Record<string, string> = {
  complete:   'var(--accent-green)',
  processing: 'var(--accent-amber)',
  error:      'var(--severity-critical)',
  pending:    'var(--text-muted)',
}

export default function Upload() {
  const qc = useQueryClient()
  const [dragging,  setDragging]  = useState(false)
  const [error,     setError]     = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const historyQ = useQuery({
    queryKey: ['uploads'],
    queryFn: getUploads,
    refetchInterval: (query) => {
      const uploads = query.state.data ?? []
      const processing = uploads.some((u: any) => u.status === 'processing' || u.status === 'pending')
      return processing ? 3000 : false
    },
  })
  const history = historyQ.data ?? []
  const fetchHistory = () => historyQ.refetch()

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadFile(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['uploads'] })
      toast.success('File uploaded successfully')
    },
    onError: (e: any) => {
      toast.error('Upload failed: ' + (e?.response?.data?.detail ?? e?.message ?? 'Unknown error'))
    },
  })
  const uploading = uploadMutation.isPending
  const result = uploadMutation.data ?? null

  const handleFile = async (file: File) => {
    setError('')
    try {
      await uploadMutation.mutateAsync(file)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? `Upload failed: ${e?.message ?? 'Unknown error'}`)
    }
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [])

  const downloadTemplate = async (type: 'spin' | 'session') => {
    const res  = await fetch(`/api/upload/template/${type}`)
    const blob = await res.blob()
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `sessionguard_${type}_template.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 860 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 'var(--space-8)' }}>Upload</h1>

      {/* ── Drop zone ──────────────────────────────────────────────────── */}
      <div
        className="card"
        onClick={() => inputRef.current?.click()}
        onDragEnter={() => setDragging(true)}
        onDragLeave={() => setDragging(false)}
        onDragOver={e => e.preventDefault()}
        onDrop={onDrop}
        style={{
          marginBottom: 'var(--space-6)',
          padding: 48,
          textAlign: 'center',
          cursor: 'pointer',
          border: `2px dashed ${dragging ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
          background: dragging ? 'rgba(59,130,246,0.04)' : 'var(--bg-surface)',
          transition: 'all var(--transition-fast)',
        }}
      >
        <div style={{ fontSize: 40, marginBottom: 12 }}>
          {uploading ? '⏳' : dragging ? '📂' : '↑'}
        </div>
        <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8 }}>
          {uploading ? 'Uploading…' : 'Drop a file or click to browse'}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          {FILE_TYPES}
        </div>
        <input ref={inputRef} type="file" accept={ACCEPT} style={{ display: 'none' }}
          onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = '' }} />
      </div>

      {/* ── Result feedback ─────────────────────────────────────────────── */}
      {error && (
        <div style={{ marginBottom: 'var(--space-4)', padding: 14, borderRadius: 'var(--radius-sm)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--severity-critical)', fontSize: 13 }}>
          ⚠ {error}
        </div>
      )}
      {result && (
        <div style={{ marginBottom: 'var(--space-4)', padding: 14, borderRadius: 'var(--radius-sm)', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)' }}>
          <div style={{ color: 'var(--accent-green)', fontWeight: 600, marginBottom: 8 }}>✓ Upload accepted</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
            <strong>{result.filename}</strong> · {result.file_type?.toUpperCase()} · Upload #{result.upload_id}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{result.processing_note}</div>
          {result.status === 'processing' && (
            <div style={{ fontSize: 11, color: 'var(--accent-amber)', marginTop: 8 }}>
              ⏳ Processing in background — upload history updates automatically below.
            </div>
          )}
        </div>
      )}

      {/* ── CSV templates ───────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>CSV Templates</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.7 }}>
          Not sure what format to use? Download a template and fill it in. <br />
          <strong style={{ color: 'var(--text-secondary)' }}>Spin-level</strong>: one row per spin (detailed). &nbsp;
          <strong style={{ color: 'var(--text-secondary)' }}>Session-level</strong>: one row per session (summary).
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          {(['spin', 'session'] as const).map(type => (
            <button key={type}
              onClick={() => downloadTemplate(type)}
              style={{
                background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
                color: 'var(--text-primary)', padding: '10px 18px',
                borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13,
                display: 'flex', alignItems: 'center', gap: 8,
              }}>
              ↓ {type === 'spin' ? 'Spin-level CSV' : 'Session-level CSV'}
            </button>
          ))}
        </div>

        {/* Column reference */}
        <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {[
            {
              title: 'Spin-level required columns',
              cols: ['date', 'bet_amount', 'win_amount', 'balance_after'],
              optional: ['game_name', 'platform', 'timestamp', 'event_type', 'confidence_score'],
            },
            {
              title: 'Session-level required columns',
              cols: ['date', 'start_balance', 'end_balance', 'total_bets', 'spins'],
              optional: ['game_name', 'platform', 'total_wins', 'biggest_win', 'losing_streak', 'duration_minutes', 'notes'],
            },
          ].map(section => (
            <div key={section.title}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{section.title}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {section.cols.map(c => (
                  <code key={c} style={{ background: 'rgba(59,130,246,0.12)', color: 'var(--accent-blue)', padding: '2px 6px', borderRadius: 4, fontSize: 11 }}>{c}</code>
                ))}
                {section.optional.map(c => (
                  <code key={c} style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', padding: '2px 6px', borderRadius: 4, fontSize: 11 }}>{c}</code>
                ))}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
                <span style={{ color: 'var(--accent-blue)' }}>■</span> required &nbsp;
                <span style={{ color: 'var(--text-muted)' }}>■</span> optional
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Upload history ───────────────────────────────────────────────── */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Upload History ({history.length})</div>
          <button onClick={fetchHistory} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>↻ Refresh</button>
        </div>
        {history.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No uploads yet.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-border)' }}>
                {['Status', 'Filename', 'Type', 'Session', 'Uploaded', 'Note'].map(h => (
                  <th key={h} style={{ padding: '6px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {history.map((u: any) => (
                <tr key={u.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                  <td style={{ padding: '10px 12px' }}>
                    <span title={u.status} style={{ fontSize: 16 }}>{STATUS_ICON[u.status] ?? '?'}</span>
                    <span style={{ fontSize: 11, color: STATUS_COLOR[u.status] ?? 'var(--text-muted)', marginLeft: 6 }}>{u.status}</span>
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-primary)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {u.filename}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className="badge badge-info" style={{ fontSize: 10 }}>{u.file_type?.toUpperCase()}</span>
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 12 }}>
                    {u.session_id ? `#${u.session_id}` : '—'}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
                    {u.created_at?.slice(0, 16) ?? '—'}
                  </td>
                  <td style={{ padding: '10px 12px', color: u.error_message ? 'var(--severity-critical)' : 'var(--text-muted)', fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {u.error_message || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
