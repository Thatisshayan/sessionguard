/**
 * src/pages/Settings.tsx — Phase 4 complete.
 * Dependency status, auth info, version, engine inventory, API quick links.
 */

import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getHealth, getVideoStatus, getOcrStatus, downloadDbBackup, restoreDb } from '../services/api'
import { toast } from '../components/Toast'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

interface DepRow { label: string; ok: boolean; detail: string; install?: string; group: string }

export default function Settings() {
  const { user } = useAuth()
  const [backingUp, setBackingUp] = useState(false)
  const [restoreFile, setRestoreFile] = useState<File | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const isAdmin = user?.role === 'admin'

  const handleBackup = async () => {
    setBackingUp(true)
    try {
      const blob = await downloadDbBackup()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `sessionguard-backup-${new Date().toISOString().slice(0, 10)}.db`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      toast.success('Database backup downloaded')
    } catch {
      toast.error('Backup download failed')
    } finally {
      setBackingUp(false)
    }
  }

  const handleRestore = async () => {
    if (!restoreFile) return
    setRestoring(true)
    try {
      await restoreDb(restoreFile)
      toast.success('Database restored — reloading…')
      setRestoreFile(null)
      setConfirmOpen(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
      window.setTimeout(() => { window.location.reload() }, 800)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      toast.error(detail ? `Restore failed: ${detail}` : 'Restore failed')
    } finally {
      setRestoring(false)
    }
  }

  const rowsQ = useQuery({
    queryKey: ['settings', 'diagnostics', !!user],
    queryFn: async () => {
      const [health, video, ocr] = await Promise.allSettled([
        getHealth(),
        getVideoStatus(),
        getOcrStatus(),
      ])
      const out: DepRow[] = []

      out.push({
        label: 'Backend (FastAPI)',
        ok:    health.status === 'fulfilled',
        detail: health.status === 'fulfilled' ? 'Running on http://127.0.0.1:8000 — 20 route groups active' : 'Not reachable — run scripts/run_backend',
        group: 'core',
      })

      out.push({
        label: 'React Frontend',
        ok:    true,
        detail: 'Running — you are viewing this page.',
        group: 'core',
      })

      out.push({
        label: 'Authentication',
        ok:    !!user,
        detail: user ? `Signed in as ${user.username} (${user.role})` : 'Not signed in — local mode (all features still accessible)',
        group: 'core',
      })

      if (video.status === 'fulfilled') {
        const v = video.value as any
        out.push({ label: 'FFmpeg', ok: v.available, detail: v.available ? v.version : v.message, install: v.available ? undefined : 'https://ffmpeg.org/download.html', group: 'pipeline' })
      }

      if (ocr.status === 'fulfilled') {
        const o = ocr.value as any
        const tess = o.backends?.tesseract
        out.push({
          label: 'Tesseract OCR',
          ok:    tess?.available,
          detail: tess?.available ? `${tess.version}` : o.message,
          install: tess?.available ? undefined : 'https://github.com/tesseract-ocr/tesseract',
          group: 'pipeline',
        })
        const easy = o.backends?.easyocr
        out.push({
          label: 'EasyOCR (optional)',
          ok:    easy?.available,
          detail: easy?.available ? 'Available — GPU-accelerated backup' : 'Not installed — optional',
          install: easy?.available ? undefined : 'pip install easyocr',
          group: 'pipeline',
        })
      }

      const engines = [
        ['Analysis Engine',      'Real metrics — RTP, drawdown, net over time, by-game'],
        ['Behavior Engine',      'sklearn — bet escalation, tilt, drift, chasing, volatility'],
        ['OCR Engine',           'Tesseract 5 — ROI crop, preprocessing, confidence scoring'],
        ['Video Pipeline',       'cv2 frame extraction + scene detection + OCR pass + event building'],
        ['Live Engine',          'Mock + screen mode — pause/resume/stop + autosave checkpoints'],
        ['Comparison Engine',    'Multi-session diff + radar data + rule-based narrative'],
        ['CSV Parser',           'Auto-detect spin-level / session-level, 30+ column aliases'],
        ['Parser Benchmark',     'OCR accuracy testing against sample frames with ROI calibration'],
        ['Export Engine',        'PDF (ReportLab 4.x + charts) + Excel (openpyxl multi-sheet)'],
        ['Job Queue',            'Thread pool executor — video, CSV, export, regenerate jobs'],
      ]
      engines.forEach(([label, detail]) => {
        out.push({ label, ok: health.status === 'fulfilled', detail, group: 'engine' })
      })

      return out
    },
  })
  const rows = rowsQ.data ?? []
  const loading = rowsQ.isPending

  const groups = [
    ['core',     'Core Services'],
    ['pipeline', 'Processing Pipeline'],
    ['engine',   'Intelligence Engines'],
  ]

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 800 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 'var(--space-8)' }}>Settings</h1>

      {loading ? (
        <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13 }}>Checking system…</div>
      ) : groups.map(([key, title]) => {
        const groupRows = rows.filter(r => r.group === key)
        if (!groupRows.length) return null
        return (
          <div key={key} className="card" style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>{title}</div>
            {groupRows.map((row, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 14, padding: '10px 0', borderBottom: i < groupRows.length - 1 ? '1px solid var(--bg-border)' : 'none' }}>
                <div style={{ fontSize: 15, marginTop: 2, flexShrink: 0 }}>{row.ok ? '✅' : '❌'}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 3 }}>{row.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{row.detail}</div>
                  {row.install && (
                    <div style={{ marginTop: 5, fontSize: 11, color: 'var(--text-muted)' }}>
                      Install:{' '}
                      <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--bg-elevated)', padding: '2px 6px', borderRadius: 4, color: 'var(--accent-blue)', fontSize: 11 }}>
                        {row.install}
                      </code>
                    </div>
                  )}
                </div>
                <span className={`badge badge-${row.ok ? 'success' : 'critical'}`} style={{ flexShrink: 0, marginTop: 2 }}>
                  {row.ok ? 'OK' : 'Missing'}
                </span>
              </div>
            ))}
          </div>
        )
      })}

      {/* Database Backup & Snapshot Card */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>
          Database Backup & Snapshot
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.6 }}>
          Download a consistent SQLite database backup snapshot generated via native <code>VACUUM INTO</code> for safe offline storage or hardware migration.
        </div>
        <button onClick={() => { void handleBackup() }} disabled={backingUp} style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'var(--accent-blue)', color: '#fff', padding: '9px 18px',
          borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600
        }}>
          {backingUp ? '⏳ Generating…' : '💾 Download Database Backup Snapshot'}
        </button>
      </div>

      {/* Database Restore Card */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>
          Database Restore
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.6 }}>
          Restore from a previously downloaded backup snapshot. The uploaded file is validated before the live
          database is replaced, and a safety copy of your current database is kept alongside it.
        </div>
        {!isAdmin ? (
          <div style={{ fontSize: 13, color: 'var(--severity-critical)' }}>Admin access required to restore the database.</div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".db,application/x-sqlite3"
              onChange={e => { setRestoreFile(e.target.files?.[0] ?? null) }}
              style={{ fontSize: 12, color: 'var(--text-secondary)' }}
            />
            <button
              className="btn-danger"
              onClick={() => { if (restoreFile) setConfirmOpen(true) }}
              disabled={!restoreFile || restoring}
            >
              {restoring ? '⏳ Restoring…' : '↩ Restore Database…'}
            </button>
          </div>
        )}
      </div>

      {/* Confirm restore modal */}
      {confirmOpen && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: 'rgba(10, 12, 16, 0.85)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div className="card" style={{ width: 460, maxWidth: '90vw', border: '1px solid var(--bg-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 700 }}>⚠️ Restore Database?</div>
              <button onClick={() => { setConfirmOpen(false) }} disabled={restoring} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}>✕</button>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 16 }}>
              This will replace the current database with the selected snapshot{restoreFile ? <> (<b style={{ color: 'var(--text-primary)' }}>{restoreFile.name}</b>)</> : null}.
              A safety copy of your current database is kept before the swap. This action cannot be undone from the UI.
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => { setConfirmOpen(false) }} disabled={restoring} style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)', padding: '9px 16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--bg-border)', cursor: 'pointer', fontSize: 13 }}>
                Cancel
              </button>
              <button onClick={() => { void handleRestore() }} disabled={restoring} style={{ background: 'var(--severity-critical)', color: '#fff', padding: '9px 16px', borderRadius: 'var(--radius-sm)', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
                {restoring ? 'Restoring…' : 'Confirm Restore'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Build info */}
      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>Build Info</div>
        {[
          ['Product',        'SessionGuard'],
          ['Version',        'v1.5.2'],
          ['Architecture',   'FastAPI + SQLite + React + PySide6 + Tesseract + cv2 + sklearn'],
          ['DB Tables',      '21 — sessions, events, users, projects, jobs, live_runs, ocr_results…'],
          ['Backend Routes', '20 route groups, 45+ endpoints'],
          ['Frontend Pages', '16 pages (Dashboard, Sessions, Detail, Compare, Live, Upload, Review, Reports, Projects, Profiles, Benchmark, Jobs, Admin, Login, Settings)'],
        ].map(([k, v]) => (
          <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '7px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 12, gap: 16 }}>
            <span style={{ color: 'var(--text-muted)', flexShrink: 0, minWidth: 140 }}>{k}</span>
            <span style={{ color: 'var(--text-secondary)', textAlign: 'right' }}>{v}</span>
          </div>
        ))}
      </div>

      {/* Quick links */}
      <div className="card">
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>API Quick Links</div>
        {[
          ['Interactive API Docs (Swagger)', 'http://127.0.0.1:8000/docs'],
          ['ReDoc API Reference',            'http://127.0.0.1:8000/redoc'],
          ['Health Check',                   'http://127.0.0.1:8000/health'],
          ['Admin Health (requires auth)',    'http://127.0.0.1:8000/admin/health'],
          ['All Sessions',                   'http://127.0.0.1:8000/sessions'],
          ['Global Metrics',                 'http://127.0.0.1:8000/metrics'],
        ].map(([label, url]) => (
          <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--bg-border)' }}>
            <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{label}</span>
            <a href={url} target="_blank" rel="noreferrer"
              style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>
              {url.replace('http://127.0.0.1:8000', '')}
            </a>
          </div>
        ))}
      </div>
    </div>
  )
}
