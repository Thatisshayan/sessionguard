/**
 * src/pages/Profiles.tsx
 * Maturity: Working Prototype — lists and creates profiles from API.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProfiles, createProfile } from '../services/api'
import { toast } from '../components/Toast'

export default function Profiles() {
  const qc = useQueryClient()
  const profilesQ = useQuery({ queryKey: ['profiles'], queryFn: getProfiles })
  const profiles = profilesQ.data ?? []
  const loading = profilesQ.isPending

  const [form,  setForm]  = useState({ name: '', game_name: '', platform: '' })
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => createProfile(data),
    onSuccess: () => {
      toast.success('Profile created')
      setForm({ name: '', game_name: '', platform: '' })
      qc.invalidateQueries({ queryKey: ['profiles'] })
    },
  })
  const creating = createMutation.isPending

  const submit = async () => {
    if (!form.name || !form.game_name || !form.platform) {
      setError('All fields are required.'); return
    }
    setError('')
    try {
      await createMutation.mutateAsync(form)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to create profile.')
      toast.error('Failed to create profile')
    }
  }

  const inputStyle = {
    background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
    color: 'var(--text-primary)', padding: '8px 12px',
    borderRadius: 'var(--radius-sm)', fontSize: 13, width: '100%',
  }

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 900 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 'var(--space-8)' }}>Profiles</h1>

      {/* Create form */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>New Profile</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 12, alignItems: 'end' }}>
          {(['name', 'game_name', 'platform'] as const).map(field => (
            <div key={field}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>
                {field.replace('_', ' ')}
              </div>
              <input
                style={inputStyle}
                value={form[field]}
                placeholder={field === 'name' ? 'e.g. Gates of Olympus — Bet365' : field === 'game_name' ? 'Gates of Olympus' : 'Bet365'}
                onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
              />
            </div>
          ))}
          <button onClick={submit} disabled={creating}
            style={{ background: 'var(--accent-blue)', color: '#fff', border: 'none', padding: '8px 20px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13, whiteSpace: 'nowrap' }}>
            {creating ? 'Creating…' : '+ Create'}
          </button>
        </div>
        {error && <div style={{ color: 'var(--severity-critical)', fontSize: 12, marginTop: 8 }}>{error}</div>}
      </div>

      {/* Profile list */}
      {loading ? <p style={{ color: 'var(--text-muted)' }}>Loading…</p> : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gutter)' }}>
          {profiles.map((p: any) => (
            <div key={p.id} className="card">
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{p.name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                {p.game_name} · {p.platform}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Alert Rules</div>
              {Object.entries(p.alert_rules ?? {}).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{String(v)}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
