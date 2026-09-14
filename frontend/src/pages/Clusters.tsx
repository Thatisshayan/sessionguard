/**
 * src/pages/Clusters.tsx
 * ------------------------
 * Session clustering explorer. Build clusters (cosine similarity on
 * session feature vectors) and browse the resulting groups.
 * Admin-only (matches the backend's require_admin on these routes).
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { buildClusters, getClusters } from '../services/api'
import { toast } from '../components/Toast'

interface ClusterMember {
  session_id: number; name: string; game_name: string
  rtp: number; net_result: number; date?: string; similarity_score?: number
}

export default function Clusters() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [threshold, setThreshold] = useState(0.88)

  const clustersQ = useQuery({ queryKey: ['clusters'], queryFn: getClusters })
  const clusters: Record<string, ClusterMember[]> = clustersQ.data?.clusters ?? {}
  const clusterCount = clustersQ.data?.cluster_count ?? 0

  const buildMutation = useMutation({
    mutationFn: () => buildClusters(threshold),
    onSuccess: (r: any) => {
      qc.invalidateQueries({ queryKey: ['clusters'] })
      toast.success(`Built ${r.cluster_count} clusters from ${r.sessions_total} sessions`)
    },
    onError: () => { toast.error('Failed to build clusters') },
  })

  const entries = Object.entries(clusters).sort((a, b) => b[1].length - a[1].length)

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 'var(--content-max-width)', margin: '0 auto' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Session Clustering</h1>
      <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 'var(--space-8)' }}>
        Groups similar sessions by RTP/streak/behavior feature vectors (cosine similarity). Re-run after importing new sessions.
      </div>

      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Build Clusters</div>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Similarity Threshold</div>
            <input type="number" min={0.5} max={1.0} step={0.01} value={threshold}
              onChange={e => setThreshold(Number(e.target.value))}
              style={{
                background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-primary)',
                padding: '8px 12px', borderRadius: 'var(--radius-sm)', fontSize: 13, width: 100,
              }} />
          </div>
          <button onClick={() => buildMutation.mutate()} disabled={buildMutation.isPending}
            style={{
              background: 'var(--accent-blue)', color: '#fff', border: 'none',
              padding: '9px 20px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            }}>
            {buildMutation.isPending ? 'Building…' : '⟳ Build Clusters'}
          </button>
        </div>
      </div>

      {clustersQ.isPending ? (
        <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading clusters…</div>
      ) : entries.length === 0 ? (
        <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          No clusters built yet. Click "Build Clusters" above to group your sessions.
        </div>
      ) : (
        <>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>{clusterCount} clusters</div>
          {entries.map(([label, members]) => (
            <div key={label} className="card" style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>Cluster {label}</div>
                <span className="badge badge-info">{members.length} session{members.length === 1 ? '' : 's'}</span>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--bg-border)' }}>
                      {['Session', 'Game', 'RTP', 'Net Result', 'Similarity'].map(h => (
                        <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {members.map(m => (
                      <tr key={m.session_id} onClick={() => navigate(`/sessions/${m.session_id}`)}
                        style={{ borderBottom: '1px solid var(--bg-border)', cursor: 'pointer' }}>
                        <td style={{ padding: '7px 10px', color: 'var(--accent-blue)' }}>{m.name}</td>
                        <td style={{ padding: '7px 10px', color: 'var(--text-secondary)' }}>{m.game_name}</td>
                        <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)' }}>{m.rtp}%</td>
                        <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', color: m.net_result >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                          ${m.net_result?.toFixed(2)}
                        </td>
                        <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {m.similarity_score != null ? m.similarity_score.toFixed(3) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
