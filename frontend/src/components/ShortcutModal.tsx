import React, { useEffect, useState } from 'react'

const SHORTCUTS = [
  { key: 'Alt + D', label: 'Go to Dashboard' },
  { key: 'Alt + S', label: 'Go to Sessions' },
  { key: 'Alt + C', label: 'Go to Compare Lab' },
  { key: 'Alt + L', label: 'Go to Live Monitor' },
  { key: 'Alt + U', label: 'Go to Upload' },
  { key: 'Alt + I', label: 'Go to Import CSV' },
  { key: 'Alt + R', label: 'Go to Review Queue' },
  { key: 'Alt + E', label: 'Go to Reports' },
  { key: 'Alt + P', label: 'Go to Profiles' },
  { key: 'Alt + J', label: 'Go to Job Queue' },
  { key: 'Alt + A', label: 'Go to Admin Panel' },
  { key: '?', label: 'Open Keyboard Shortcuts Cheat-sheet' },
]

export function ShortcutModal() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === '?') {
        e.preventDefault()
        setOpen(o => !o)
      } else if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open])

  if (!open) return null

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(10, 12, 16, 0.85)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center'
    }}>
      <div className="card" style={{ width: 480, maxWidth: '90vw', border: '1px solid var(--bg-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 700 }}>⌨️ Keyboard Shortcuts</div>
          <button onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}>✕</button>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: 12 }}>
          {SHORTCUTS.map(s => (
            <div key={s.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'var(--bg-elevated)', borderRadius: 4 }}>
              <span style={{ color: 'var(--text-secondary)' }}>{s.label}</span>
              <kbd style={{ fontFamily: 'var(--font-mono)', background: 'var(--bg-surface)', padding: '2px 6px', borderRadius: 3, border: '1px solid var(--bg-border)', fontSize: 10 }}>{s.key}</kbd>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16, fontSize: 11, color: 'var(--text-muted)', textAlign: 'right' }}>
          Press Esc to close
        </div>
      </div>
    </div>
  )
}
