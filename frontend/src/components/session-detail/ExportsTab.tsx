/**
 * src/components/session-detail/ExportsTab.tsx
 * -------------------------------------------------
 * Export generation (PDF/Excel/JSON/CSV) + export history/download list.
 * Also generates/verifies the evidence package: a ZIP bundling the PDF
 * report, events CSV, insights, alerts, OCR results, and frame thumbnails
 * behind a SHA-256 manifest — registered as a regular export
 * (format='evidence') so it shares the same history/download flow.
 */

interface ExportRecord { id: number; format: string; file_path: string; created_at: string }

export function ExportsTab({ exports_, exporting, onExport, onGenerateEvidence, generatingEvidence, onVerifyEvidence, verifyingEvidence }: {
  exports_: ExportRecord[]
  exporting: string
  onExport: (fmt: string) => void
  onGenerateEvidence: () => void
  generatingEvidence: boolean
  onVerifyEvidence: () => void
  verifyingEvidence: boolean
}) {
  const hasEvidence = exports_.some(ex => ex.format === 'evidence')

  return (
    <div>
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Generate Export</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {[
            { fmt: 'pdf',   label: 'PDF Report',     icon: '📄' },
            { fmt: 'excel', label: 'Excel Workbook',  icon: '📊' },
            { fmt: 'json',  label: 'JSON Data',       icon: '{}' },
            { fmt: 'csv',   label: 'CSV Export',      icon: '≡'  },
          ].map(({ fmt, label, icon }) => (
            <button key={fmt} onClick={() => onExport(fmt)} disabled={!!exporting}
              style={{
                background: exporting === fmt ? 'var(--accent-blue)' : 'var(--bg-elevated)',
                border: `1px solid ${exporting === fmt ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
                color: exporting === fmt ? '#fff' : 'var(--text-primary)',
                padding: '12px 20px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
                fontSize: 13, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8,
              }}>
              <span style={{ fontSize: 18 }}>{icon}</span>
              {exporting === fmt ? 'Generating…' : label}
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Evidence Package</div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.6 }}>
          A single ZIP bundling the PDF report, events CSV, insights, alerts, OCR results, and frame
          thumbnails, with a SHA-256 manifest so integrity can be verified later.
        </div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button onClick={onGenerateEvidence} disabled={generatingEvidence}
            style={{
              background: generatingEvidence ? 'var(--accent-blue)' : 'var(--bg-elevated)',
              border: `1px solid ${generatingEvidence ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
              color: generatingEvidence ? '#fff' : 'var(--text-primary)',
              padding: '12px 20px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
              fontSize: 13, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8,
            }}>
            <span style={{ fontSize: 18 }}>🔒</span>
            {generatingEvidence ? 'Generating…' : 'Generate Evidence Package'}
          </button>
          {hasEvidence && (
            <button onClick={onVerifyEvidence} disabled={verifyingEvidence}
              style={{
                background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)',
                padding: '12px 20px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
                fontSize: 13, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8,
              }}>
              <span style={{ fontSize: 18 }}>✓</span>
              {verifyingEvidence ? 'Verifying…' : 'Verify Manifest Integrity'}
            </button>
          )}
        </div>
      </div>

      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Export History</div>
        {exports_.length === 0
          ? <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No exports for this session yet.</div>
          : exports_.map(ex => (
            <div key={ex.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--bg-border)' }}>
              <div>
                <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  {ex.format === 'evidence' && <span className="badge badge-info" style={{ fontSize: 9 }}>evidence</span>}
                  {ex.file_path.split('/').pop()}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{ex.created_at.slice(0, 16)}</div>
              </div>
              <button
                onClick={() => window.open(`http://127.0.0.1:8000/exports/${ex.id}/download`, '_blank')}
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12 }}>
                ↓ Download
              </button>
            </div>
          ))
        }
      </div>
    </div>
  )
}
