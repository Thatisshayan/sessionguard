/**
 * src/components/NotificationCenter.tsx
 * ----------------------------------------
 * In-app notification center. Connects to WebSocket and displays
 * real-time push notifications for alerts, job completions, insights.
 * Shows as a bell icon in the top bar with a dropdown list.
 * Maturity: Working Prototype
 */

import { useEffect, useState, useRef } from 'react'

interface Notification {
  id:        number
  type:      'alert' | 'job_complete' | 'insight' | 'live_event' | 'system'
  title:     string
  message:   string
  timestamp: number
  read:      boolean
  severity?: string
}

const TYPE_ICON: Record<string, string> = {
  alert:        '🔴',
  job_complete: '✅',
  insight:      '💡',
  live_event:   '⏱',
  system:       'ℹ',
}

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--severity-critical)',
  warning:  'var(--severity-warning)',
  info:     'var(--accent-blue)',
}

export function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [open,          setOpen]          = useState(false)
  const [wsStatus,      setWsStatus]      = useState<'connecting'|'connected'|'disconnected'>('connecting')
  const wsRef    = useRef<WebSocket | null>(null)
  const idRef    = useRef(0)
  const panelRef = useRef<HTMLDivElement>(null)

  const unread = notifications.filter(n => !n.read).length

  // ── WebSocket connection ────────────────────────────────────────────────────
  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket('ws://127.0.0.1:8000/ws/global')
        ws.onopen = () => setWsStatus('connected')
        ws.onclose = () => {
          setWsStatus('disconnected')
          setTimeout(connect, 5000)
        }
        ws.onerror = () => ws.close()
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.type === 'ping' || msg.type === 'pong' || msg.type === 'connected') return

            const note: Notification = {
              id:        ++idRef.current,
              type:      msg.type,
              title:     _title(msg),
              message:   _message(msg),
              timestamp: Date.now(),
              read:      false,
              severity:  msg.data?.severity,
            }
            setNotifications(prev => [note, ...prev].slice(0, 50))
          } catch { /* malformed message */ }
        }
        wsRef.current = ws
      } catch {
        setWsStatus('disconnected')
        setTimeout(connect, 5000)
      }
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  // Close panel on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const markAllRead = () =>
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))

  const clearAll = () => setNotifications([])

  const elapsed = (ts: number) => {
    const s = Math.floor((Date.now() - ts) / 1000)
    if (s < 60)  return `${s}s ago`
    if (s < 3600) return `${Math.floor(s/60)}m ago`
    return `${Math.floor(s/3600)}h ago`
  }

  return (
    <div ref={panelRef} style={{ position: 'relative', display: 'inline-block' }}>
      {/* Bell button */}
      <button
        onClick={() => { setOpen(o => !o); if (!open) setNotifications(p => p.map(n => ({...n, read: true}))) }}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          position: 'relative', padding: '6px 8px',
          color: unread > 0 ? 'var(--accent-blue)' : 'var(--text-muted)',
          fontSize: 18, lineHeight: 1,
        }}
        title="Notifications">
        🔔
        {unread > 0 && (
          <span style={{
            position: 'absolute', top: 2, right: 2,
            background: 'var(--severity-critical)', color: '#fff',
            borderRadius: '50%', width: 16, height: 16,
            fontSize: 9, fontWeight: 700, lineHeight: '16px',
            textAlign: 'center', display: 'block',
          }}>{unread > 9 ? '9+' : unread}</span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, zIndex: 1000,
          width: 340, background: 'var(--bg-surface)',
          border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-md)',
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
        }}>
          {/* Header */}
          <div style={{
            padding: '12px 14px', borderBottom: '1px solid var(--bg-border)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>Notifications</div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <div style={{ width: 6, height: 6, borderRadius: '50%', background: wsStatus === 'connected' ? 'var(--accent-green)' : 'var(--text-muted)' }} />
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {wsStatus === 'connected' ? 'Live' : 'Offline'}
              </span>
              {notifications.length > 0 && (
                <>
                  <button onClick={markAllRead} style={{ background:'none',border:'none',color:'var(--accent-blue)',cursor:'pointer',fontSize:11 }}>Mark read</button>
                  <button onClick={clearAll} style={{ background:'none',border:'none',color:'var(--text-muted)',cursor:'pointer',fontSize:11 }}>Clear</button>
                </>
              )}
            </div>
          </div>

          {/* List */}
          <div style={{ maxHeight: 360, overflowY: 'auto' }}>
            {notifications.length === 0 ? (
              <div style={{ padding: '32px 14px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                <div style={{ fontSize: 28, marginBottom: 8 }}>🔔</div>
                No notifications yet.<br/>
                <span style={{ fontSize: 11 }}>Alerts, job completions and insights appear here in real time.</span>
              </div>
            ) : notifications.map(n => (
              <div key={n.id} style={{
                padding: '10px 14px',
                borderBottom: '1px solid var(--bg-border)',
                background: n.read ? 'transparent' : 'rgba(59,130,246,0.06)',
                opacity: n.read ? 0.75 : 1,
              }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <span style={{ fontSize: 15, flexShrink: 0 }}>{TYPE_ICON[n.type] ?? 'ℹ'}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 12, fontWeight: 600, marginBottom: 2,
                      color: SEV_COLOR[n.severity ?? ''] ?? 'var(--text-primary)',
                    }}>{n.title}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{n.message}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{elapsed(n.timestamp)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Message builders ──────────────────────────────────────────────────────────
function _title(msg: any): string {
  switch (msg.type) {
    case 'alert':        return `Alert — ${msg.data?.severity?.toUpperCase() ?? 'INFO'}`
    case 'job_complete': return `Job complete — ${msg.data?.job_type ?? 'task'}`
    case 'insight':      return `New insight — ${msg.data?.severity ?? 'info'}`
    case 'live_event':   return 'Live event'
    default:             return 'Notification'
  }
}
function _message(msg: any): string {
  switch (msg.type) {
    case 'alert':        return msg.data?.message ?? 'New alert fired.'
    case 'job_complete': return `${msg.data?.job_type} finished in ${msg.data?.duration_s ?? '?'}s`
    case 'insight':      return msg.data?.text?.slice(0, 100) ?? 'New insight generated.'
    case 'live_event':   return `Run #${msg.run_id} — ${msg.data?.event_type ?? 'event'}`
    default:             return JSON.stringify(msg.data ?? {}).slice(0, 80)
  }
}
