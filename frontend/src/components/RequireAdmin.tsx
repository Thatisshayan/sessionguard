/**
 * src/components/RequireAdmin.tsx
 * ----------------------------------
 * Route guard for admin-only pages. Redirects to /login while auth is
 * still loading or unauthenticated, and to / if authenticated but not
 * an admin. General route-level auth (P0.6) stays deferred — SessionGuard
 * is confirmed single-user-local for now — so this guard is scoped to
 * /admin only, the one place that already assumed an admin check.
 */

import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { loading, user, isAdmin } = useAuth()

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
      Loading…
    </div>
  )

  if (!user) return <Navigate to="/login" replace />
  if (!isAdmin) return <Navigate to="/" replace />

  return <>{children}</>
}
