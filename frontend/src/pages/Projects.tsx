/**
 * src/pages/Projects.tsx
 * -----------------------
 * Create, list, and manage projects.
 * Sessions can be grouped under projects for team workflows.
 * Maturity: Working Prototype
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import axios from 'axios'
import { toast } from '../components/Toast'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

interface Project {
  id:          number
  name:        string
  description: string
  owner_id:    number
  owner_name:  string
  tags:        string[]
  sessions:    any[]
  members:     any[]
  created_at:  string
  updated_at:  string
}

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
  color: 'var(--text-primary)', padding: '8px 12px',
  borderRadius: 'var(--radius-sm)', fontSize: 13, width: '100%',
}

export default function Projects() {
  const { accessToken, user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [form,       setForm]       = useState({ name: '', description: '', tags: '' })
  const [error,      setError]      = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : {}

  const projectsQ = useQuery({
    queryKey: ['projects', accessToken],
    queryFn: async () => {
      try {
        const res = await axios.get(`${BASE}/projects`, { headers })
        return res.data as Project[]
      } catch (e: any) {
        if (e?.response?.status === 401) navigate('/login')
        throw e
      }
    },
  })
  const projects = projectsQ.data ?? []
  const loading = projectsQ.isPending

  const selectedQ = useQuery({
    queryKey: ['projects', selectedId],
    queryFn: async () => (await axios.get(`${BASE}/projects/${selectedId}`, { headers })).data as Project,
    enabled: selectedId != null,
  })
  const selected = selectedQ.data ?? null

  const createMutation = useMutation({
    mutationFn: () => axios.post(`${BASE}/projects`, {
      name:        form.name,
      description: form.description,
      tags:        form.tags.split(',').map(t => t.trim()).filter(Boolean),
    }, { headers }),
    onSuccess: () => {
      toast.success('Project created')
      setForm({ name: '', description: '', tags: '' })
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
  const creating = createMutation.isPending

  const createProject = async () => {
    if (!form.name.trim()) { setError('Project name is required.'); return }
    setError('')
    try {
      await createMutation.mutateAsync()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to create project.')
      toast.error('Operation failed')
    }
  }

  const deleteMutation = useMutation({
    mutationFn: (id: number) => axios.delete(`${BASE}/projects/${id}`, { headers }),
    onSuccess: (_r, id) => {
      toast.success('Project deleted')
      qc.invalidateQueries({ queryKey: ['projects'] })
      if (selectedId === id) setSelectedId(null)
    },
    onError: () => {
      toast.error('Operation failed')
    },
  })

  const deleteProject = (id: number) => {
    if (!confirm('Delete this project?')) return
    deleteMutation.mutate(id)
  }

  const loadProject = (id: number) => setSelectedId(id)

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 1100 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 'var(--space-8)' }}>Projects</h1>

      {/* Create form */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>New Project</div>
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 1fr auto', gap: 12, alignItems: 'end' }}>
          {[
            { field: 'name',        label: 'Project Name',  placeholder: 'Q4 Slot Analysis' },
            { field: 'description', label: 'Description',   placeholder: 'Optional description' },
            { field: 'tags',        label: 'Tags (comma)',   placeholder: 'slots, high-risk' },
          ].map(({ field, label, placeholder }) => (
            <div key={field}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 5, textTransform: 'uppercase' }}>{label}</div>
              <input style={inputStyle} value={(form as any)[field]}
                onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                placeholder={placeholder} />
            </div>
          ))}
          <button onClick={createProject} disabled={creating}
            style={{ background: 'var(--accent-blue)', border: 'none', color: '#fff', padding: '9px 18px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
            {creating ? '…' : '+ Create'}
          </button>
        </div>
        {error && <div style={{ color: 'var(--severity-critical)', fontSize: 12, marginTop: 8 }}>{error}</div>}
      </div>

      {/* Projects grid */}
      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
      ) : projects.length === 0 ? (
        <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: 40 }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📁</div>
          No projects yet. Create one above to group your sessions.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 2fr' : '1fr 1fr 1fr', gap: 'var(--gutter)' }}>
          {/* Project list */}
          <div style={{ gridColumn: selected ? 1 : 'auto' }}>
            {projects.map(p => (
              <div key={p.id} className="card"
                style={{ marginBottom: 'var(--gutter)', cursor: 'pointer', borderColor: selected?.id === p.id ? 'var(--accent-blue)' : 'var(--bg-border)', transition: 'border-color var(--transition-fast)' }}
                onClick={() => loadProject(p.id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{p.name}</div>
                    {p.description && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{p.description}</div>}
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {(p.tags || []).map(tag => (
                        <span key={tag} style={{ background: 'rgba(59,130,246,0.12)', color: 'var(--accent-blue)', padding: '2px 8px', borderRadius: 99, fontSize: 10 }}>{tag}</span>
                      ))}
                    </div>
                  </div>
                  {(p.owner_id === user?.id || user?.role === 'admin') && (
                    <button onClick={e => { e.stopPropagation(); deleteProject(p.id) }}
                      style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16, padding: '0 4px' }}>×</button>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>Owner: {p.owner_name}</span>
                  <span>{p.sessions?.length ?? 0} sessions</span>
                  <span>{p.members?.length ?? 0} members</span>
                </div>
              </div>
            ))}
          </div>

          {/* Project detail */}
          {selected && (
            <div>
              <div className="card" style={{ marginBottom: 'var(--gutter)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{selected.name}</div>
                  <button onClick={() => setSelectedId(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>×</button>
                </div>

                {/* Sessions in project */}
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sessions ({selected.sessions.length})</div>
                {selected.sessions.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No sessions linked yet. Add sessions from the Sessions page.</div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--bg-border)' }}>
                        {['Game', 'Date', 'Net', 'RTP', 'Status'].map(h => (
                          <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 10, textTransform: 'uppercase' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {selected.sessions.map(s => (
                        <tr key={s.id} style={{ borderBottom: '1px solid var(--bg-border)', cursor: 'pointer' }}
                          onClick={() => navigate(`/sessions/${s.id}`)}>
                          <td style={{ padding: '8px 10px' }}>{s.game_name}</td>
                          <td style={{ padding: '8px 10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>{s.date}</td>
                          <td style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)', color: s.net_result >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {s.net_result >= 0 ? '+' : ''}${s.net_result?.toFixed(2)}
                          </td>
                          <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>{s.rtp}%</td>
                          <td style={{ padding: '8px 10px' }}><span className={`badge badge-${s.status === 'flagged' ? 'warning' : 'success'}`} style={{ fontSize: 9 }}>{s.status}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                {/* Members */}
                {selected.members.length > 0 && (
                  <>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', margin: '16px 0 10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Members ({selected.members.length})</div>
                    {selected.members.map(m => (
                      <div key={m.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 12 }}>
                        <span style={{ color: 'var(--text-primary)' }}>{m.username}</span>
                        <span className="badge badge-info" style={{ fontSize: 9 }}>{m.role}</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
