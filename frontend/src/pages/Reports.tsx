/**
 * src/pages/Reports.tsx
 * Maturity: Working Prototype — all four formats implemented (PDF, Excel, JSON, CSV).
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { createExport, getExports, getSessions } from '../services/api'
import type { Session } from '../services/api'

const FORMATS = [
  { key: 'pdf',   label: 'PDF Report',    icon: '📄', desc: 'Styled report with charts & insights' },
  { key: 'excel', label: 'Excel',         icon: '📊', desc: 'Multi-sheet workbook with raw data' },
  { key: 'json',  label: 'JSON',          icon: '{ }', desc: 'Machine-readable metrics export' },
  { key: 'csv',   label: 'CSV',           icon: '≡',  desc: 'Sessions table as plain CSV' },
]

export default function Reports() {
  const qc = useQueryClient()
  const sessionsQ = useQuery({ queryKey: ['sessions', { limit: 100 }], queryFn: () => getSessions({ limit: 100 }) })
  const exportsQ  = useQuery({ queryKey: ['exports', 'all'], queryFn: () => getExports() })
  const sessions: Session[] = sessionsQ.data ?? []
  const exports_ = exportsQ.data ?? []

  const [sessionId, setSessionId] = useState<string>('global')
  const [error,      setError]    = useState('')

  const generateMutation = useMutation({
    mutationFn: (fmt: string) => {
      const sid = sessionId === 'global' ? undefined : Number(sessionId)
      return createExport(fmt, sid)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['exports', 'all'] }),
  })
  const generating = generateMutation.isPending ? (generateMutation.variables ?? '') : ''
  const result = generateMutation.data ?? null

  const generate = async (fmt: string) => {
    setError('')
    try {
      await generateMutation.mutateAsync(fmt)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Export failed.')
    }
  }

  const extIcon: Record<string, string> = {
    pdf: '📄', excel: '📊', json: '{ }', csv: '≡'
  }

  const sel: React.CSSProperties = {
    background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
    color: 'var(--text-primary)', padding: '8px 12px',
    borderRadius: 'var(--radius-sm)', fontSize: 13, width: '100%',
  }

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 900 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 'var(--space-8)' }}>Reports &amp; Exports</h1>

      {/* ── Generator ──────────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Generate Export</div>

        {/* Session selector */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Scope</div>
          <select value={sessionId} onChange={e => setSessionId(e.target.value)} style={{ ...sel, maxWidth: 400 }}>
            <option value="global">Global Summary — All Sessions</option>
            {sessions.map(s => (
              <option key={s.id} value={String(s.id)}>
                #{s.id} · {s.name} ({s.date})
              </option>
            ))}
          </select>
        </div>

        {/* Format buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
          {FORMATS.map(f => (
            <button key={f.key}
              onClick={() => generate(f.key)}
              disabled={!!generating}
              style={{
                background: generating === f.key ? 'var(--accent-blue)' : 'var(--bg-elevated)',
                border: `1px solid ${generating === f.key ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
                color: generating === f.key ? '#fff' : 'var(--text-primary)',
                padding: '14px 12px', borderRadius: 'var(--radius-md)',
                cursor: generating ? 'not-allowed' : 'pointer',
                textAlign: 'left', transition: 'all var(--transition-fast)',
              }}>
              <div style={{ fontSize: 20, marginBottom: 6 }}>{f.icon}</div>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                {generating === f.key ? 'Generating…' : f.label}
              </div>
              <div style={{ fontSize: 11, color: generating === f.key ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)' }}>
                {f.desc}
              </div>
            </button>
          ))}
        </div>

        {/* Result */}
        {result && (
          <div style={{
            padding: 12, borderRadius: 'var(--radius-sm)',
            background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)',
          }}>
            <div style={{ color: 'var(--accent-green)', fontWeight: 600, marginBottom: 4, fontSize: 13 }}>
              ✓ Export complete
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              {result.filename}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              File saved to storage/exports/ — use the download button below to retrieve it.
            </div>
          </div>
        )}
        {error && (
          <div style={{ padding: 12, borderRadius: 'var(--radius-sm)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--severity-critical)', fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>

      {/* ── Export history ──────────────────────────────────────────────── */}
      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>
          Export History ({exports_.length})
        </div>
        {exports_.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No exports generated yet.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-border)' }}>
                {['Format', 'Filename', 'Session', 'Generated'].map(h => (
                  <th key={h} style={{ padding: '6px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {exports_.map((ex: any) => (
                <tr key={ex.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                  <td style={{ padding: '10px 12px' }}>
                    <span style={{ fontSize: 16, marginRight: 6 }}>{extIcon[ex.format] ?? '📁'}</span>
                    <span className="badge badge-info" style={{ fontSize: 10 }}>{ex.format?.toUpperCase()}</span>
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>
                    {ex.file_path?.split('/').pop() ?? '—'}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 12 }}>
                    {ex.session_id ? `Session #${ex.session_id}` : 'Global'}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
                    {ex.created_at?.slice(0, 16) ?? '—'}
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
