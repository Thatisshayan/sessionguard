/**
 * src/components/UpdateBanner.tsx — Slim top banner when update is available.
 * Polls /updater/check on mount and every 4 hours.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { toast } from './Toast'

const BASE = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
const POLL_MS = 4 * 60 * 60 * 1000

interface UpdateInfo {
  current_version: string; latest_version: string; update_available: boolean
  download_url?: string | null; release_url?: string | null; release_notes?: string | null
  published_at?: string | null; dismissed_version?: string | null; is_dismissed?: boolean; error?: string | null
}
function norm(v?: string | null) { return String(v || '').trim().replace(/^v/i, '') }

export default function UpdateBanner() {
  const [info, setInfo]           = useState<UpdateInfo | null>(null)
  const [visible, setVisible]     = useState(false)
  const [expanded, setExpanded]   = useState(false)
  const [dismissing, setDismiss]  = useState(false)

  const releaseUrl = useMemo(() => info?.release_url || info?.download_url || '', [info])

  const shouldShow = useCallback((d: UpdateInfo) => {
    if (!d.update_available || !norm(d.latest_version)) return false
    if (d.is_dismissed) return false
    if (d.dismissed_version && norm(d.dismissed_version) === norm(d.latest_version)) return false
    return true
  }, [])

  const check = useCallback(async () => {
    try {
      const res = await axios.get<UpdateInfo>(`${BASE}/updater/check`, { timeout: 12000 })
      setInfo(res.data); setVisible(shouldShow(res.data))
    } catch { setVisible(false) }
  }, [shouldShow])

  useEffect(() => {
    check()
    const t = window.setInterval(check, POLL_MS)
    return () => window.clearInterval(t)
  }, [check])

  const handleDownload = () => { if (releaseUrl) window.open(releaseUrl, '_blank', 'noopener,noreferrer') }
  const handleDismiss  = async () => {
    if (!info?.latest_version) { setVisible(false); return }
    setDismiss(true)
    try { await axios.post(`${BASE}/updater/dismiss`, { version: info.latest_version }, { timeout: 12000 }); toast.info('Update dismissed') }
    catch { toast.error('Failed to dismiss update') } finally { setVisible(false); setDismiss(false) }
  }

  if (!visible || !info) return null
  const notes = info.release_notes?.trim()
  const pub   = info.published_at ? new Date(info.published_at).toLocaleDateString() : null

  return (
    <div style={{ position:'sticky', top:0, zIndex:9999, width:'100%',
      background:'var(--bg-surface)', borderBottom:'2px solid var(--accent-blue)',
      boxShadow:'0 4px 16px rgba(59,130,246,0.15)' }} role="status">
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'10px 20px', gap:12 }}>
        <div>
          <div style={{ fontSize:13, fontWeight:700 }}>
            🚀 SessionGuard v{norm(info.latest_version)} is available
            <span style={{ marginLeft:8, color:'var(--text-muted)', fontWeight:400, fontSize:12 }}>
              (you have v{norm(info.current_version)}{pub ? ` · released ${pub}` : ''})
            </span>
          </div>
          {notes && <button onClick={() => setExpanded(e => !e)} style={{ padding:0, border:'none',
            background:'transparent', color:'var(--accent-blue)', cursor:'pointer', fontSize:11, marginTop:2 }}>
            {expanded ? '▲ Hide notes' : '▼ Show release notes'}
          </button>}
        </div>
        <div style={{ display:'flex', gap:8, flexShrink:0 }}>
          <button onClick={handleDownload} disabled={!releaseUrl}
            style={{ border:'none', background:'var(--accent-blue)', color:'#fff',
              borderRadius:999, padding:'7px 16px', cursor:'pointer', fontWeight:700, fontSize:13 }}>
            Download
          </button>
          <button onClick={handleDismiss} disabled={dismissing}
            style={{ border:'1px solid var(--bg-border)', background:'transparent',
              color:'var(--text-muted)', borderRadius:999, padding:'7px 14px', cursor:'pointer', fontSize:12 }}>
            {dismissing ? '…' : 'Dismiss'}
          </button>
        </div>
      </div>
      {expanded && notes && (
        <div style={{ borderTop:'1px solid var(--bg-border)', padding:'10px 20px 12px',
          color:'var(--text-muted)', fontSize:12, lineHeight:1.6,
          whiteSpace:'pre-wrap', maxHeight:160, overflowY:'auto' }}>
          {notes}
        </div>
      )}
    </div>
  )
}
