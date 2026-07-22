/**
 * src/context/AuthContext.tsx
 * ----------------------------
 * Global auth state using React Context.
 * Stores access + refresh tokens in memory (sessionStorage for persistence).
 * Provides login/logout/refresh helpers used across the app.
 *
 * Maturity: Working Prototype
 * Future:   Replace sessionStorage with httpOnly cookies (V7).
 */

import {
  createContext, useContext, useState, useEffect,
  useCallback, type ReactNode,
} from 'react'
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

export interface AuthUser {
  id:       number
  email:    string
  username: string
  role:     string
}

interface AuthState {
  user:         AuthUser | null
  accessToken:  string | null
  loading:      boolean
  login:        (email: string, password: string) => Promise<void>
  logout:       () => Promise<void>
  signup:       (email: string, username: string, password: string) => Promise<void>
  refreshToken: () => Promise<boolean>
  isAdmin:      boolean
}

const AuthContext = createContext<AuthState | null>(null)

const STORAGE_KEY_REFRESH = 'sg_refresh_token'
const STORAGE_KEY_USER    = 'sg_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,        setUser]        = useState<AuthUser | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [loading,     setLoading]     = useState(true)

  // ── Restore session on mount ───────────────────────────────────────────────
  useEffect(() => {
    const savedUser    = sessionStorage.getItem(STORAGE_KEY_USER)
    const savedRefresh = sessionStorage.getItem(STORAGE_KEY_REFRESH)
    if (savedUser && savedRefresh) {
      try {
        setUser(JSON.parse(savedUser))
        // Refresh access token immediately
        _doRefresh(savedRefresh).catch(() => {
          sessionStorage.clear()
          setUser(null)
        })
      } catch {
        sessionStorage.clear()
      }
    }
    setLoading(false)
  }, [])

  const _doRefresh = async (rawRefresh: string): Promise<string> => {
    const res = await axios.post(`${BASE}/auth/refresh`, {
      refresh_token: rawRefresh,
    })
    const { access_token, refresh_token } = res.data
    setAccessToken(access_token)
    sessionStorage.setItem(STORAGE_KEY_REFRESH, refresh_token)
    return access_token
  }

  // ── Login ──────────────────────────────────────────────────────────────────
  const login = useCallback(async (email: string, password: string) => {
    const res = await axios.post(`${BASE}/auth/login`, { email, password })
    const { access_token, refresh_token, user: u } = res.data
    setAccessToken(access_token)
    setUser(u)
    sessionStorage.setItem(STORAGE_KEY_REFRESH, refresh_token)
    sessionStorage.setItem(STORAGE_KEY_USER, JSON.stringify(u))
  }, [])

  // ── Signup ─────────────────────────────────────────────────────────────────
  const signup = useCallback(async (email: string, username: string, password: string) => {
    await axios.post(`${BASE}/auth/signup`, { email, username, password })
    // Auto-login after signup
    await login(email, password)
  }, [login])

  // ── Logout ─────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    const refreshTok = sessionStorage.getItem(STORAGE_KEY_REFRESH)
    if (refreshTok && accessToken) {
      try {
        await axios.post(`${BASE}/auth/logout`, { refresh_token: refreshTok }, {
          headers: { Authorization: `Bearer ${accessToken}` },
        })
      } catch { /* ignore network errors on logout */ }
    }
    setAccessToken(null)
    setUser(null)
    sessionStorage.removeItem(STORAGE_KEY_REFRESH)
    sessionStorage.removeItem(STORAGE_KEY_USER)
  }, [accessToken])

  // ── Refresh ────────────────────────────────────────────────────────────────
  const refreshToken = useCallback(async (): Promise<boolean> => {
    const raw = sessionStorage.getItem(STORAGE_KEY_REFRESH)
    if (!raw) return false
    try {
      await _doRefresh(raw)
      return true
    } catch {
      setUser(null); setAccessToken(null)
      sessionStorage.clear()
      return false
    }
  }, [])

  return (
    <AuthContext.Provider value={{
      user, accessToken, loading,
      login, logout, signup, refreshToken,
      isAdmin: user?.role === 'admin',
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}

// ── Axios interceptor helper (call once at app start) ─────────────────────────
export function makeAuthClient(getToken: () => string | null) {
  const client = axios.create({ baseURL: BASE, timeout: 15_000 })
  client.interceptors.request.use(cfg => {
    const tok = getToken()
    if (tok) cfg.headers.set('Authorization', `Bearer ${tok}`)
    return cfg
  })
  return client
}
