/**
 * src/components/session-detail/ExportsTab.tsx
 * -------------------------------------------------
 * Export generation (PDF/Excel/JSON/CSV) + export history/download list.
 */

export function ExportsTab({ exports_, exporting, onExport }: {
  exports_: any[]
  exporting: string
  onExport: (fmt: string) => void
}) {
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

      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Export History</div>
        {exports_.length === 0
          ? <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No exports for this session yet.</div>
          : exports_.map((ex: any) => (
            <div key={ex.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--bg-border)' }}>
              <div>
                <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{ex.file_path?.split('/').pop()}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{ex.created_at?.slice(0, 16)}</div>
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
