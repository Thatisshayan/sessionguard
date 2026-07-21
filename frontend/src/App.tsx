/**
 * src/App.tsx â€” SessionGuard Phase 7 final.
 * 18 pages + NotificationCenter in top bar + keyboard shortcut listener.
 * All routes wired. AuthProvider. WebSocket status dot.
 */

import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { useEffect, useRef, useState } from 'react'
import { NotificationCenter } from './components/NotificationCenter'

// â”€â”€ Pages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
import Dashboard       from './pages/Dashboard'
import Sessions        from './pages/Sessions'
import SessionDetail   from './pages/SessionDetail'
import Compare         from './pages/Compare'
import LiveMonitor     from './pages/LiveMonitor'
import Upload          from './pages/Upload'
import ReviewQueue     from './pages/ReviewQueue'
import Reports         from './pages/Reports'
import Projects        from './pages/Projects'
import Profiles        from './pages/Profiles'
import ProfileEditor   from './pages/ProfileEditor'
import ParserBenchmark from './pages/ParserBenchmark'
import JobsMonitor     from './pages/JobsMonitor'
import Admin           from './pages/Admin'
import Login           from './pages/Login'
import Settings        from './pages/Settings'
import VideoLab        from './pages/VideoLab'
import ImportWizard    from './pages/ImportWizard'

// â”€â”€ WebSocket status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function useWsStatus() {
  const [ok, setOk] = useState(false)
  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket('ws://127.0.0.1:8000/ws/global')
        ws.onopen  = () => setOk(true)
        ws.onclose = () => { setOk(false); setTimeout(connect, 5000) }
        ws.onerror = () => ws.close()
      } catch { setOk(false); setTimeout(connect, 5000) }
    }
    connect()
  }, [])
  return ok
}

// â”€â”€ Keyboard shortcuts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function useKeyboardShortcuts() {
  const navigate = useNavigate()
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (!e.altKey) return
      const shortcuts: Record<string, string> = {
        'd': '/',
        's': '/sessions',
        'c': '/compare',
        'l': '/live',
        'u': '/upload',
        'i': '/import',
        'r': '/review',
        'e': '/reports',
        'p': '/profiles',
        'j': '/jobs',
        'a': '/admin',
      }
      const target = shortcuts[e.key.toLowerCase()]
      if (target) { e.preventDefault(); navigate(target) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate])
}

// â"€â"€ Add Import CSV to keyboard shortcuts â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
function useKeyboardShortcutsWithImport() {
  const navigate = useNavigate()
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (!e.altKey) return
      const shortcuts: Record<string, string> = {
        'd': '/',
        's': '/sessions',
        'c': '/compare',
        'l': '/live',
        'u': '/upload',
        'i': '/import',
        'r': '/review',
        'e': '/reports',
        'p': '/profiles',
        'j': '/jobs',
        'a': '/admin',
      }
      const target = shortcuts[e.key.toLowerCase()]
      if (target) { e.preventDefault(); navigate(target) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [navigate])
}

// â”€â”€ Nav config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const NAV_MAIN = [
  { to: '/',         label: 'Dashboard',    icon: 'â–£', shortcut: 'D', end: true  },
  { to: '/sessions', label: 'Sessions',     icon: 'â‰¡', shortcut: 'S', end: false },
  { to: '/compare',  label: 'Compare Lab',  icon: 'â‡Œ', shortcut: 'C', end: false },
  { to: '/live',     label: 'Live Monitor', icon: 'â±', shortcut: 'L', end: false },
  { to: '/upload',   label: 'Upload',       icon: 'â†’', shortcut: 'U', end: false },
  { to: '/import',   label: 'Import CSV',   icon: 'ðŸ"„', shortcut: 'I', end: false },
  { to: '/review',   label: 'Review Queue', icon: 'â—ˆ', shortcut: 'R', end: false },
  { to: '/reports',  label: 'Reports',      icon: 'âŠ¡', shortcut: 'E', end: false },
  { to: '/projects', label: 'Projects',     icon: 'ðŸ“', shortcut: '',  end: false },
]
const NAV_TOOLS = [
  { to: '/profiles',  label: 'Profiles',         icon: 'â—Ž', shortcut: 'P', end: false },
  { to: '/benchmark', label: 'Parser Benchmark',  icon: 'âŠ—', shortcut: '',  end: false },
  { to: '/jobs',      label: 'Job Queue',         icon: 'âš™', shortcut: 'J', end: false },
]
const NAV_ADMIN  = [{ to: '/admin',    label: 'Admin Panel',  icon: 'ðŸ”', shortcut: 'A', end: false }]
const NAV_BOTTOM = [{ to: '/settings', label: 'Settings',     icon: 'âš™', shortcut: '',  end: false }]

// â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Sidebar({ wsOk }: { wsOk: boolean }) {
  const { user, logout, isAdmin } = useAuth()
  useKeyboardShortcuts()

  const Item = ({ to, label, icon, shortcut = '', end = false }: {
    to: string; label: string; icon: string; shortcut?: string; end?: boolean
  }) => (
    <NavLink to={to} end={end}
      style={({ isActive }) => ({
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 12px', borderRadius: 'var(--radius-sm)',
        color:      isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
        background: isActive ? 'var(--bg-elevated)' : 'transparent',
        fontWeight: isActive ? 600 : 400, textDecoration: 'none',
        fontSize: 13, marginBottom: 1,
        borderLeft: isActive ? '2px solid var(--accent-blue)' : '2px solid transparent',
        transition: 'all var(--transition-fast)',
      })}>
      <span style={{ fontSize: 12, width: 16, textAlign: 'center', opacity: 0.8 }}>{icon}</span>
      <span style={{ flex: 1 }}>{label}</span>
      {shortcut && <span style={{ fontSize: 9, color: 'var(--text-muted)', background: 'var(--bg-elevated)', padding: '1px 5px', borderRadius: 3, fontFamily: 'var(--font-mono)' }}>Alt+{shortcut}</span>}
    </NavLink>
  )

  const Sec = ({ label }: { label: string }) => (
    <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '10px 12px 4px' }}>{label}</div>
  )

  return (
    <aside style={{
      width: 'var(--sidebar-width)', minWidth: 'var(--sidebar-width)',
      background: 'var(--bg-surface)', borderRight: '1px solid var(--bg-border)',
      display: 'flex', flexDirection: 'column',
      height: '100vh', position: 'sticky', top: 0, overflowY: 'auto',
    }}>
      {/* Logo */}
      <div style={{ padding: 'var(--space-6)', borderBottom: '1px solid var(--bg-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.02em' }}>
            <span style={{ color: 'var(--accent-blue)' }}>Session</span>
            <span style={{ color: 'var(--text-primary)' }}>Guard</span>
          </div>
          <div title={wsOk ? 'WebSocket live' : 'WebSocket offline'}
            style={{ width: 7, height: 7, borderRadius: '50%', background: wsOk ? 'var(--accent-green)' : 'var(--text-muted)' }} />
        </div>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          v0.8 Â· Phase 7
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: 'var(--space-3)', overflowY: 'auto' }}>
        <Sec label="Analytics" />
        {NAV_MAIN.map(i => <Item key={i.to} {...i} />)}
        <Sec label="Tools" />
        {NAV_TOOLS.map(i => <Item key={i.to} {...i} />)}
        {isAdmin && (<><Sec label="Admin" />{NAV_ADMIN.map(i => <Item key={i.to} {...i} />)}</>)}
      </nav>

      {/* User footer */}
      <div style={{ padding: 'var(--space-3)', borderTop: '1px solid var(--bg-border)' }}>
        {NAV_BOTTOM.map(i => <Item key={i.to} {...i} />)}
        {user ? (
          <div style={{ margin: '6px 0', padding: '10px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{user.username}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 8 }}>{user.email}</div>
            <button onClick={logout} style={{ width: '100%', background: 'none', border: '1px solid var(--bg-border)', color: 'var(--text-muted)', padding: '5px', borderRadius: 4, cursor: 'pointer', fontSize: 11 }}>
              Sign out
            </button>
          </div>
        ) : (
          <NavLink to="/login" style={{ display: 'block', margin: '6px 0', padding: '9px 12px', background: 'var(--accent-blue)', borderRadius: 'var(--radius-sm)', color: '#fff', textDecoration: 'none', fontSize: 13, fontWeight: 600, textAlign: 'center' }}>
            Sign In
          </NavLink>
        )}
        <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.8 }}>
          {wsOk ? 'â— Live' : 'â—‹ Offline'} Â· Alt+key to navigate
        </div>
      </div>
    </aside>
  )
}

// â”€â”€ Top bar with notification center â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function TopBar() {
  return (
    <div style={{
      position: 'sticky', top: 0, zIndex: 100,
      background: 'rgba(10,12,16,0.92)', backdropFilter: 'blur(8px)',
      borderBottom: '1px solid var(--bg-border)',
      padding: '0 var(--page-margin)',
      display: 'flex', justifyContent: 'flex-end', alignItems: 'center',
      height: 44,
    }}>
      <NotificationCenter />
    </div>
  )
}

// â”€â”€ App shell â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function AppShell() {
  const { loading } = useAuth()
  const wsOk = useWsStatus()

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--bg-base)', color: 'var(--text-muted)', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 32 }}>â³</div>SessionGuard loadingâ€¦
    </div>
  )

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar wsOk={wsOk} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar />
        <main style={{ flex: 1, overflow: 'auto', background: 'var(--bg-base)' }}>
          <Routes>
            <Route path="/login"             element={<Login />} />
            <Route path="/"                  element={<Dashboard />} />
            <Route path="/sessions"          element={<Sessions />} />
            <Route path="/sessions/:id"      element={<SessionDetail />} />
            <Route path="/sessions/:id/video" element={<VideoLab />} />
            <Route path="/compare"           element={<Compare />} />
            <Route path="/live"              element={<LiveMonitor />} />
            <Route path="/import" element={<ImportWizard />} /><Route path="/upload"            element={<Upload />} />
            <Route path="/review"            element={<ReviewQueue />} />
            <Route path="/reports"           element={<Reports />} />
            <Route path="/projects"          element={<Projects />} />
            <Route path="/profiles"          element={<Profiles />} />
            <Route path="/profiles/new"      element={<ProfileEditor />} />
            <Route path="/profiles/:id/edit" element={<ProfileEditor />} />
            <Route path="/benchmark"         element={<ParserBenchmark />} />
            <Route path="/jobs"              element={<JobsMonitor />} />
            <Route path="/admin"             element={<Admin />} />
            <Route path="/settings"          element={<Settings />} />
            <Route path="*"                  element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell />
      </AuthProvider>
    </BrowserRouter>
  )
}

