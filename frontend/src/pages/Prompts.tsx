/**
 * src/pages/Prompts.tsx
 * -------------------------
 * AI prompt version management + A/B comparison results.
 * Admin-only (matches the backend's require_admin on these routes).
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getPromptVersions, activatePromptVersion, createPromptVersion, getAbResults,
  type PromptVersion,
} from '../services/api'
import { toast } from '../components/Toast'

export default function Prompts() {
  const qc = useQueryClient()
  const [showNew, setShowNew] = useState(false)
  const [newPrompt, setNewPrompt] = useState('')
  const [newModel, setNewModel] = useState('nvidia/llama-3.1-nemotron-70b-instruct')
  const [newTemp, setNewTemp] = useState(1.0)

  const versionsQ = useQuery({ queryKey: ['prompts'], queryFn: () => getPromptVersions() })
  const abQ = useQuery({ queryKey: ['prompts', 'ab'], queryFn: () => getAbResults() })
  const versions: PromptVersion[] = versionsQ.data ?? []
  const abResults: any[] = abQ.data ?? []

  const activateMutation = useMutation({
    mutationFn: (id: number) => activatePromptVersion(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['prompts'] }); toast.success('Prompt version activated') },
    onError: () => { toast.error('Failed to activate prompt version') },
  })

  const createMutation = useMutation({
    mutationFn: () => createPromptVersion({ system_prompt: newPrompt, model: newModel, temperature: newTemp }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['prompts'] })
      toast.success('Prompt version created')
      setShowNew(false); setNewPrompt('')
    },
    onError: () => { toast.error('Failed to create prompt version') },
  })

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 'var(--content-max-width)', margin: '0 auto' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Prompt Versioning</h1>
      <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 'var(--space-8)' }}>
        Manage system prompt versions for AI session analysis, and review A/B comparison outcomes.
      </div>

      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showNew ? 16 : 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Versions ({versions.length})</div>
          <button onClick={() => setShowNew(v => !v)} style={{
            background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)',
            padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12,
          }}>
            {showNew ? 'Cancel' : '+ New Version'}
          </button>
        </div>

        {showNew && (
          <div style={{ marginBottom: 16, padding: 14, background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)' }}>
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>System Prompt</div>
              <textarea value={newPrompt} onChange={e => setNewPrompt(e.target.value)} rows={4}
                style={{
                  width: '100%', background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-primary)',
                  padding: '8px 12px', borderRadius: 'var(--radius-sm)', fontSize: 12, fontFamily: 'var(--font-mono)', resize: 'vertical',
                }} />
            </div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Model</div>
                <input value={newModel} onChange={e => setNewModel(e.target.value)}
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-primary)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', fontSize: 12, width: 280 }} />
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Temperature</div>
                <input type="number" min={0} max={2} step={0.1} value={newTemp} onChange={e => setNewTemp(Number(e.target.value))}
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-primary)', padding: '8px 12px', borderRadius: 'var(--radius-sm)', fontSize: 12, width: 80 }} />
              </div>
            </div>
            <button onClick={() => createMutation.mutate()} disabled={!newPrompt.trim() || createMutation.isPending}
              style={{ background: 'var(--accent-blue)', color: '#fff', border: 'none', padding: '8px 18px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              {createMutation.isPending ? 'Creating…' : 'Create Version'}
            </button>
          </div>
        )}

        {versionsQ.isPending ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
        ) : versions.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No prompt versions yet.</div>
        ) : versions.map(v => (
          <div key={v.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--bg-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>v{v.version}</span>
                {!!v.is_active && <span className="badge badge-success">active</span>}
                <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{v.model}</span>
              </div>
              {!v.is_active && (
                <button onClick={() => activateMutation.mutate(v.id)} disabled={activateMutation.isPending}
                  style={{ background: 'none', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '4px 10px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 11 }}>
                  Activate
                </button>
              )}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', background: 'var(--bg-base)', padding: '8px 10px', borderRadius: 'var(--radius-sm)', maxHeight: 80, overflow: 'auto' }}>
              {v.system_prompt}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>A/B Comparison Results ({abResults.length})</div>
        {abQ.isPending ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
        ) : abResults.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No A/B results recorded yet.</div>
        ) : abResults.map(r => (
          <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 12 }}>
            <div>
              <span style={{ color: 'var(--text-secondary)' }}>Session {r.session_id}</span>
              <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>#{r.prompt_a_id} vs #{r.prompt_b_id}</span>
            </div>
            <span className="badge badge-info">{r.winner ?? 'no winner recorded'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
