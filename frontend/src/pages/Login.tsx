/**
 * src/pages/Login.tsx
 * --------------------
 * Login + signup page. Redirects to dashboard on success.
 * Maturity: Working Prototype
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { toast } from '../components/Toast'

type Mode = 'login' | 'signup'

const inputStyle: React.CSSProperties = {
  width: '100%',
  background: 'var(--bg-elevated)',
  border: '1px solid var(--bg-border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text-primary)',
  padding: '10px 14px',
  fontSize: 14,
  outline: 'none',
}

const btnStyle: React.CSSProperties = {
  width: '100%',
  background: 'var(--accent-blue)',
  border: 'none',
  borderRadius: 'var(--radius-sm)',
  color: '#fff',
  padding: '12px',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
  marginTop: 8,
}

export default function Login() {
  const navigate    = useNavigate()
  const { login, signup } = useAuth()
  const [mode,     setMode]     = useState<Mode>('login')
  const [email,    setEmail]    = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')

  const handleSubmit = async () => {
    setLoading(true); setError('')
    try {
      if (mode === 'login') {
        await login(email, password)
        toast.success('Welcome back!')
      } else {
        if (!username.trim()) { setError('Username is required.'); setLoading(false); return }
        if (password.length < 6) { setError('Password must be at least 6 characters.'); setLoading(false); return }
        await signup(email, username, password)
        toast.success('Account created')
      }
      navigate('/')
    } catch (e: any) {
      toast.error('Authentication failed')
      const detail = e?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Authentication failed. Check credentials.')
    } finally { setLoading(false) }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-base)',
    }}>
      <div style={{ width: 380 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 8 }}>
            <span style={{ color: 'var(--accent-blue)' }}>Session</span>
            <span style={{ color: 'var(--text-primary)' }}>Guard</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Session Intelligence Platform · v0.6
          </div>
        </div>

        {/* Card */}
        <div className="card">
          {/* Tab toggle */}
          <div style={{ display: 'flex', marginBottom: 24, background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', padding: 4 }}>
            {(['login', 'signup'] as Mode[]).map(m => (
              <button key={m} onClick={() => { setMode(m); setError('') }}
                style={{
                  flex: 1, padding: '8px', borderRadius: 'var(--radius-sm)',
                  border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                  background: mode === m ? 'var(--accent-blue)' : 'transparent',
                  color:      mode === m ? '#fff' : 'var(--text-secondary)',
                  textTransform: 'capitalize',
                }}>
                {m === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          {/* Fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Email</label>
              <input style={inputStyle} type="email" value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                placeholder="you@example.com" />
            </div>

            {mode === 'signup' && (
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Username</label>
                <input style={inputStyle} type="text" value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="yourusername" />
              </div>
            )}

            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Password</label>
              <input style={inputStyle} type="password" value={password}
                onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                placeholder="••••••••" />
            </div>

            {error && (
              <div style={{ padding: '10px 12px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-sm)', color: 'var(--severity-critical)', fontSize: 13 }}>
                {error}
              </div>
            )}

            <button style={{ ...btnStyle, opacity: loading ? 0.6 : 1 }}
              onClick={handleSubmit} disabled={loading}>
              {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </div>

        </div>

        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 12, color: 'var(--text-muted)' }}>
          Local-first build · Demo account may exist in seeded data
        </div>
      </div>
    </div>
  )
}
