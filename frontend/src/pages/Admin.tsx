/**
 * src/pages/Admin.tsx
 * --------------------
 * Admin panel — system health, user management, job queue, audit log.
 * Only accessible to users with role=admin.
 * Maturity: Working Prototype
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

type AdminTab = 'health' | 'users' | 'jobs' | 'audit'

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="card" style={{ flex: 1, minWidth: 130 }}>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'var(--font-mono)', color: accent ?? 'var(--text-primary)' }}>{value}</div>
    </div>
  )
}

export default function Admin() {
  const { accessToken, user, isAdmin } = useAuth()
  const qc = useQueryClient()
  const [tab, setTab] = useState<AdminTab>('health')

  const hdrs = { headers: { Authorization: `Bearer ${accessToken}` } }

  const adminQ = useQuery({
    queryKey: ['admin', 'all', accessToken],
    queryFn: async () => {
      const [h, s, u, j, a] = await Promise.all([
        axios.get(`${BASE}/admin/health`,  hdrs).then(r => r.data),
        axios.get(`${BASE}/admin/stats`,   hdrs).then(r => r.data),
        axios.get(`${BASE}/admin/users`,   hdrs).then(r => r.data),
        axios.get(`${BASE}/jobs?limit=50`, hdrs).then(r => r.data),
        axios.get(`${BASE}/admin/audit?limit=50`, hdrs).then(r => r.data),
      ])
      return { health: h, stats: s, users: u, jobs: j, audit: a }
    },
    enabled: isAdmin,
  })
  const health = adminQ.data?.health ?? null
  const stats  = adminQ.data?.stats ?? null
  const users  = adminQ.data?.users ?? []
  const jobs   = adminQ.data?.jobs ?? []
  const audit  = adminQ.data?.audit ?? []
  const loading = adminQ.isPending
  const fetchAll = () => adminQ.refetch()

  const patchUserMutation = useMutation({
    mutationFn: ({ uid, patch }: { uid: number; patch: any }) => axios.patch(`${BASE}/admin/users/${uid}`, patch, hdrs),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'all'] }),
  })

  const toggleUser = (uid: number, isActive: boolean) => patchUserMutation.mutate({ uid, patch: { is_active: !isActive } })
  const changeRole = (uid: number, role: string) => patchUserMutation.mutate({ uid, patch: { role } })

  const TAB = (key: AdminTab, label: string) => (
    <button key={key} onClick={() => setTab(key)}
      style={{
        background: tab === key ? 'var(--accent-blue)' : 'var(--bg-elevated)',
        border: `1px solid ${tab === key ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
        color: tab === key ? '#fff' : 'var(--text-secondary)',
        padding: '6px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 500,
      }}>{label}</button>
  )

  if (!isAdmin) return null
  if (loading) return <div style={{ padding: 'var(--page-margin)', color: 'var(--text-muted)' }}>Loading admin panel…</div>

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 'var(--content-max-width)', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-8)' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Admin Panel</h1>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Logged in as {user?.username} ({user?.role})</div>
        </div>
        <button onClick={fetchAll} style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '7px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>↻ Refresh</button>
      </div>

      {/* Stats strip */}
      {stats && (
        <div style={{ display: 'flex', gap: 'var(--gutter)', marginBottom: 'var(--space-8)', flexWrap: 'wrap' }}>
          <StatCard label="Sessions"        value={stats.sessions} />
          <StatCard label="Events"          value={stats.events?.toLocaleString()} />
          <StatCard label="Users"           value={stats.users} />
          <StatCard label="Projects"        value={stats.projects} />
          <StatCard label="Pending Reviews" value={stats.pending_reviews} accent={stats.pending_reviews > 0 ? 'var(--severity-warning)' : undefined} />
          <StatCard label="Unacked Alerts"  value={stats.unacked_alerts}  accent={stats.unacked_alerts > 0  ? 'var(--severity-critical)' : undefined} />
          <StatCard label="Running Jobs"    value={stats.running_jobs}    accent={stats.running_jobs > 0    ? 'var(--accent-green)' : undefined} />
          <StatCard label="Exports"         value={stats.exports} />
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-6)' }}>
        {TAB('health', 'System Health')}
        {TAB('users',  'Users')}
        {TAB('jobs',   'Job Queue')}
        {TAB('audit',  'Audit Log')}
      </div>

      {/* ── System Health ── */}
      {tab === 'health' && health && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gutter)' }}>
          <div className="card">
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>Dependencies</div>
            {Object.entries(health.dependencies ?? {}).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 13 }}>
                <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{k}</span>
                <span className={`badge badge-${v ? 'success' : 'critical'}`}>{v ? 'OK' : 'Missing'}</span>
              </div>
            ))}
          </div>
          <div className="card">
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>DB Table Counts</div>
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {Object.entries(health.table_counts ?? {}).map(([t, c]) => (
                <div key={t} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 12 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>{t}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{String(c)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Users ── */}
      {tab === 'users' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-border)', background: 'var(--bg-elevated)' }}>
                {['ID', 'Email', 'Username', 'Role', 'Status', 'Last Login', 'Actions'].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                  <td style={{ padding: '9px 12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>#{u.id}</td>
                  <td style={{ padding: '9px 12px', color: 'var(--text-primary)' }}>{u.email}</td>
                  <td style={{ padding: '9px 12px', color: 'var(--text-secondary)' }}>{u.username}</td>
                  <td style={{ padding: '9px 12px' }}>
                    <select value={u.role}
                      onChange={e => changeRole(u.id, e.target.value)}
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-primary)', padding: '3px 8px', borderRadius: 4, fontSize: 12 }}>
                      {['user', 'editor', 'admin'].map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td style={{ padding: '9px 12px' }}>
                    <span className={`badge badge-${u.is_active ? 'success' : 'critical'}`}>{u.is_active ? 'active' : 'disabled'}</span>
                  </td>
                  <td style={{ padding: '9px 12px', color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>{u.last_login?.slice(0,16) || '—'}</td>
                  <td style={{ padding: '9px 12px' }}>
                    <button onClick={() => toggleUser(u.id, u.is_active)}
                      disabled={u.id === user?.id}
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: u.is_active ? 'var(--severity-warning)' : 'var(--accent-green)', padding: '4px 10px', borderRadius: 4, cursor: u.id === user?.id ? 'not-allowed' : 'pointer', fontSize: 11 }}>
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Job Queue ── */}
      {tab === 'jobs' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--bg-border)', fontSize: 13, fontWeight: 600 }}>Job Queue ({jobs.length})</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-border)', background: 'var(--bg-elevated)' }}>
                {['ID', 'Type', 'Status', 'Progress', 'Session', 'Created', 'Duration'].map(h => (
                  <th key={h} style={{ padding: '7px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 10, textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => {
                const statusColor: Record<string, string> = { complete: 'var(--accent-green)', error: 'var(--severity-critical)', running: 'var(--accent-blue)', pending: 'var(--text-muted)', cancelled: 'var(--text-muted)' }
                const dur = j.started_at && j.completed_at
                  ? `${((new Date(j.completed_at).getTime() - new Date(j.started_at).getTime()) / 1000).toFixed(1)}s`
                  : j.started_at ? 'running…' : '—'
                return (
                  <tr key={j.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                    <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 11 }}>#{j.id}</td>
                    <td style={{ padding: '8px 12px' }}><span className="badge badge-info" style={{ fontSize: 9 }}>{j.job_type}</span></td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ color: statusColor[j.status] ?? 'var(--text-muted)', fontWeight: 600, fontSize: 11 }}>{j.status}</span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <div style={{ background: 'var(--bg-base)', borderRadius: 3, height: 6, width: 80 }}>
                        <div style={{ background: 'var(--accent-blue)', height: '100%', borderRadius: 3, width: `${j.progress ?? 0}%` }} />
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{j.progress ?? 0}%</div>
                    </td>
                    <td style={{ padding: '8px 12px', color: 'var(--text-muted)', fontSize: 11 }}>{j.session_id ? `#${j.session_id}` : '—'}</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 10 }}>{j.created_at?.slice(0,16)}</td>
                    <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', fontSize: 11 }}>{dur}</td>
                  </tr>
                )
              })}
              {jobs.length === 0 && (
                <tr><td colSpan={7} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No jobs yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Audit Log ── */}
      {tab === 'audit' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--bg-border)', fontSize: 13, fontWeight: 600 }}>Audit Log ({audit.length} recent)</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-border)', background: 'var(--bg-elevated)' }}>
                {['Time', 'User', 'Action', 'Resource'].map(h => (
                  <th key={h} style={{ padding: '7px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 10, textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {audit.map(a => (
                <tr key={a.id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                  <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 10 }}>{a.created_at?.slice(0,19)}</td>
                  <td style={{ padding: '7px 12px', color: 'var(--text-secondary)' }}>{a.username ?? 'system'}</td>
                  <td style={{ padding: '7px 12px' }}><span className="badge badge-info" style={{ fontSize: 9 }}>{a.action}</span></td>
                  <td style={{ padding: '7px 12px', color: 'var(--text-muted)', fontSize: 11 }}>{a.resource || '—'}</td>
                </tr>
              ))}
              {audit.length === 0 && (
                <tr><td colSpan={4} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>No audit entries yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
