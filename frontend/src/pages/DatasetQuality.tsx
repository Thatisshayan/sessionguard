/**
 * src/pages/DatasetQuality.tsx
 * -------------------------------
 * Dataset quality report (completeness, distribution, compliance/self-audit)
 * + statistically anomalous sessions (z-score on RTP/net result).
 * Admin-only (matches the backend's require_admin on these routes).
 */

import { useState } from 'react'
import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getDatasetQuality, getAnomalies } from '../services/api'

interface DatasetQualityReport {
  total_sessions: number; total_events: number
  completeness: Record<string, Record<string, number>>
  game_distribution: Array<{ game_name: string; count: number }>
  confidence_distribution: Array<{ bucket: string; count: number }>
  net_result_stats: { avg: number | null; avg_rtp: number | null }
}
interface Anomaly {
  session_id: number; session_name: string; game_name: string
  rtp: number; net_result: number; reasons: string[]; severity: string
}

function Pct({ value }: { value: number }) {
  const color = value >= 0.95 ? 'var(--accent-green)' : value >= 0.8 ? 'var(--accent-amber)' : 'var(--severity-critical)'
  return <span style={{ color, fontFamily: 'var(--font-mono)' }}>{(value * 100).toFixed(0)}%</span>
}

function QualityReport({ q }: { q: DatasetQualityReport }) {
  return (
    <>
      <div style={{ display: 'flex', gap: 'var(--gutter)', marginBottom: 'var(--space-6)', flexWrap: 'wrap' }}>
        {[
          ['Total Sessions', q.total_sessions],
          ['Total Events', q.total_events],
          ['Avg Net Result', q.net_result_stats.avg != null ? `$${q.net_result_stats.avg}` : '—'],
          ['Avg RTP', q.net_result_stats.avg_rtp != null ? `${q.net_result_stats.avg_rtp}%` : '—'],
        ].map(([label, val]) => (
          <div key={label as string} className="card" style={{ flex: 1, minWidth: 140 }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{val}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>Field Completeness</div>
        {Object.entries(q.completeness).map(([table, cols]) => (
          <div key={table} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>{table}</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
              {Object.entries(cols).map(([col, val]) => (
                <div key={col} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 10px', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{col}</span>
                  <Pct value={val} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gutter)', marginBottom: 'var(--space-6)' }}>
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Game Distribution</div>
          {q.game_distribution.map(g => (
            <div key={g.game_name} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', fontSize: 12, borderBottom: '1px solid var(--bg-border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>{g.game_name}</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{g.count}</span>
            </div>
          ))}
        </div>
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Confidence Distribution</div>
          {q.confidence_distribution.map(c => (
            <div key={c.bucket} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', fontSize: 12, borderBottom: '1px solid var(--bg-border)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>{c.bucket}</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{c.count}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

type ThresholdHandler = (zThreshold: number) => void

function AnomaliesSection({ anomaliesQ, zThreshold, onThreshold }: {
  anomaliesQ: UseQueryResult<Anomaly[]>
  zThreshold: number
  onThreshold: ThresholdHandler
}) {
  const anomalies = anomaliesQ.data ?? []
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>Anomalous Sessions</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Z-threshold</span>
          <input type="number" min={1} max={4} step={0.5} value={zThreshold}
            onChange={e => {
              const v = Number(e.target.value)
              if (Number.isFinite(v)) onThreshold(Math.min(4, Math.max(1, v)))
            }}
            style={{
              background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-primary)',
              padding: '5px 8px', borderRadius: 'var(--radius-sm)', fontSize: 12, width: 60,
            }} />
        </div>
      </div>
      {anomaliesQ.isPending ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
      ) : anomaliesQ.isError ? (
        <div style={{ color: 'var(--severity-critical)', fontSize: 13 }}>Failed to load anomalies.</div>
      ) : anomalies.length === 0 ? (
        <div style={{ color: 'var(--accent-green)', fontSize: 13 }}>✓ No anomalous sessions at this threshold.</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-border)' }}>
                {['Session', 'Game', 'RTP', 'Net Result', 'Reasons', ''].map(h => (
                  <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {anomalies.map(a => (
                <tr key={a.session_id} style={{ borderBottom: '1px solid var(--bg-border)' }}>
                  <td style={{ padding: '7px 10px' }}>{a.session_name}</td>
                  <td style={{ padding: '7px 10px', color: 'var(--text-secondary)' }}>{a.game_name}</td>
                  <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)' }}>{a.rtp}%</td>
                  <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)' }}>${a.net_result.toFixed(2)}</td>
                  <td style={{ padding: '7px 10px', color: 'var(--text-muted)', fontSize: 11 }}>{a.reasons.join('; ')}</td>
                  <td style={{ padding: '7px 10px' }}>
                    <span className={`badge badge-${a.severity === 'critical' ? 'critical' : 'warning'}`}>{a.severity}</span>
                    <Link to={`/sessions/${a.session_id}`}
                      style={{ marginLeft: 8, color: 'var(--accent-blue)', fontSize: 11 }}>
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function DatasetQuality() {
  const [zThreshold, setZThreshold] = useState(2.0)

  const qualityQ = useQuery({ queryKey: ['dataset-quality'], queryFn: getDatasetQuality })
  const anomaliesQ = useQuery({ queryKey: ['anomalies', zThreshold], queryFn: () => getAnomalies(zThreshold) })

  const q: DatasetQualityReport | undefined = qualityQ.data

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 'var(--content-max-width)', margin: '0 auto' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Dataset Quality Report</h1>
      <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 'var(--space-8)' }}>
        Completeness, distribution, and anomaly detection across all sessions — for compliance and self-audit.
      </div>

      {qualityQ.isPending ? (
        <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
      ) : qualityQ.isError || !q ? (
        <div className="card" style={{ color: 'var(--severity-critical)', fontSize: 13 }}>Failed to load dataset quality report.</div>
      ) : (
        <QualityReport q={q} />
      )}

      <AnomaliesSection anomaliesQ={anomaliesQ} zThreshold={zThreshold} onThreshold={setZThreshold} />
    </div>
  )
}
