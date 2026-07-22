/**
 * src/pages/ParserBenchmark.tsx
 * ------------------------------
 * OCR accuracy testing UI.
 * Upload sample frames → select profile ROI → run benchmark → see confidence scores.
 * Maturity: Working Prototype
 */

import { useEffect, useState, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import axios from 'axios'
import { getProfiles } from '../services/api'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

interface FrameResult {
  frame:              string
  overall_confidence: number
  flagged:            boolean
  fields: {
    balance?: { value: number | null; confidence: number; low_conf: boolean }
    bet?:     { value: number | null; confidence: number; low_conf: boolean }
    win?:     { value: number | null; confidence: number; low_conf: boolean }
  }
}

interface BenchmarkResult {
  frame_count:       number
  avg_confidence:    number
  low_conf_count:    number
  flagged_count:     number
  recommendation:    string
  results:           FrameResult[]
}

function ConfBar({ value }: { value: number }) {
  const color = value >= 0.90 ? 'var(--accent-green)' : value >= 0.75 ? 'var(--accent-amber)' : 'var(--severity-critical)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ background: 'var(--bg-base)', borderRadius: 3, height: 6, width: 80, flexShrink: 0 }}>
        <div style={{ background: color, height: '100%', borderRadius: 3, width: `${value * 100}%` }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color }}>{(value * 100).toFixed(0)}%</span>
    </div>
  )
}

export default function ParserBenchmark() {
  const [profileId, setProfileId] = useState<string>('')
  const [roiJson,   setRoiJson]   = useState('{}')
  const [error,     setError]     = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const profilesQ = useQuery({ queryKey: ['profiles'], queryFn: getProfiles })
  const profiles = profilesQ.data ?? []

  useEffect(() => {
    if (profiles.length > 0 && !profileId) {
      setProfileId(String(profiles[0].id))
      setRoiJson(JSON.stringify(profiles[0].roi_config ?? {}, null, 2))
    }
  }, [profiles])

  const handleProfileChange = (id: string) => {
    setProfileId(id)
    const p = profiles.find((p: any) => String(p.id) === id)
    if (p) setRoiJson(JSON.stringify(p.roi_config ?? {}, null, 2))
  }

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('roi_config', roiJson)
      return axios.post(`${BASE}/parser-benchmark/upload-frame`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then(res => res.data as BenchmarkResult)
    },
  })
  const runMutation = useMutation({
    mutationFn: () => axios.post(`${BASE}/parser-benchmark`, {
      frame_paths: [],
      profile_id:  Number(profileId),
    }).then(res => res.data as BenchmarkResult),
  })

  const loading = uploadMutation.isPending || runMutation.isPending
  const result: BenchmarkResult | null = uploadMutation.data ?? runMutation.data ?? null

  const handleUpload = async (file: File) => {
    setError('')
    try {
      await uploadMutation.mutateAsync(file)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Benchmark failed.')
    }
  }

  const runWithFramePaths = async () => {
    if (!profileId) { setError('Select a profile first.'); return }
    setError('')
    try {
      await runMutation.mutateAsync()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to run benchmark.')
    }
  }

  const selStyle: React.CSSProperties = {
    background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
    color: 'var(--text-primary)', padding: '8px 12px',
    borderRadius: 'var(--radius-sm)', fontSize: 13,
  }

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 900 }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Parser Benchmark</h1>
      <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 'var(--space-8)' }}>
        Test OCR accuracy on sample frames to calibrate your profile's ROI coordinates.
      </div>

      {/* Config */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Configuration</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gutter)', marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Profile</div>
            <select value={profileId} onChange={e => handleProfileChange(e.target.value)} style={{ ...selStyle, width: '100%' }}>
              <option value="">— None (use custom ROI) —</option>
              {profiles.map(p => <option key={p.id} value={String(p.id)}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>ROI Config (JSON)</div>
            <textarea value={roiJson} onChange={e => setRoiJson(e.target.value)} rows={4}
              style={{ ...selStyle, width: '100%', fontFamily: 'var(--font-mono)', fontSize: 11, resize: 'vertical' }} />
          </div>
        </div>

        {/* ROI reference */}
        <div style={{ padding: '10px 14px', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <strong style={{ color: 'var(--text-primary)' }}>ROI format:</strong>{' '}
          <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>
            {`{"balance_region":[x,y,w,h],"bet_region":[x,y,w,h],"win_region":[x,y,w,h],"scale":2.0}`}
          </code>
          <div style={{ marginTop: 4, color: 'var(--text-muted)' }}>Coordinates are in pixels. Scale 2.0 = double resolution before OCR (recommended).</div>
        </div>
      </div>

      {/* Upload zone */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Upload Frame for Testing</div>
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={e => e.preventDefault()}
          onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleUpload(f) }}
          style={{
            padding: '32px', textAlign: 'center', cursor: 'pointer',
            border: '2px dashed var(--bg-border)', borderRadius: 'var(--radius-md)',
            background: loading ? 'rgba(59,130,246,0.04)' : 'transparent',
            transition: 'all var(--transition-fast)',
          }}>
          <div style={{ fontSize: 28, marginBottom: 10 }}>{loading ? '⏳' : '🖼'}</div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{loading ? 'Running OCR…' : 'Drop a screenshot here or click to browse'}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>PNG, JPEG — use a real game screenshot for accurate results</div>
          <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }}
            onChange={e => { const f = e.target.files?.[0]; if (f) handleUpload(f); e.target.value = '' }} />
        </div>
        {error && <div style={{ marginTop: 12, color: 'var(--severity-critical)', fontSize: 13 }}>{error}</div>}
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Summary */}
          <div className="card" style={{ marginBottom: 'var(--space-6)', borderColor: result.avg_confidence >= 0.85 ? 'var(--accent-green)' : result.avg_confidence >= 0.75 ? 'var(--accent-amber)' : 'var(--severity-critical)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>Benchmark Summary</div>
            <div style={{ display: 'flex', gap: 'var(--gutter)', marginBottom: 14, flexWrap: 'wrap' }}>
              {[
                ['Frames Tested', result.frame_count],
                ['Avg Confidence', `${(result.avg_confidence * 100).toFixed(0)}%`],
                ['Low Conf Frames', result.low_conf_count],
                ['Flagged', result.flagged_count],
              ].map(([label, val]) => (
                <div key={label} className="card" style={{ flex: 1, minWidth: 120 }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{val}</div>
                </div>
              ))}
            </div>
            <div style={{ padding: '10px 14px', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', fontSize: 13, color: 'var(--text-secondary)' }}>
              💡 {result.recommendation}
            </div>
          </div>

          {/* Per-frame results */}
          {result.results.map((r, i) => (
            <div key={i} className="card" style={{ marginBottom: 'var(--space-4)', borderColor: r.flagged ? 'var(--severity-warning)' : 'var(--bg-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {r.frame.split('/').pop()}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {r.flagged && <span className="badge badge-warning">flagged</span>}
                  <ConfBar value={r.overall_confidence} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                {Object.entries(r.fields).map(([fname, fdata]: [string, any]) => (
                  <div key={fname} style={{ background: 'var(--bg-base)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: `1px solid ${fdata.low_conf ? 'rgba(245,158,11,0.3)' : 'var(--bg-border)'}` }}>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6 }}>{fname}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 700, color: fdata.value != null ? 'var(--text-primary)' : 'var(--text-muted)', marginBottom: 6 }}>
                      {fdata.value != null ? `$${fdata.value.toFixed(2)}` : 'Not detected'}
                    </div>
                    <ConfBar value={fdata.confidence} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </>
      )}

      {/* Tips */}
      <div className="card" style={{ marginTop: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Calibration Tips</div>
        {[
          ['Low confidence', 'Increase scale to 2.5–3.0, or try threshold=128 for high-contrast backgrounds.'],
          ['Wrong values', 'Adjust ROI x/y/width/height coordinates — use a screenshot editor to measure pixel positions.'],
          ['Not detected', 'The region may be outside the cropped area. Increase width/height or move x/y.'],
          ['Works on some frames', 'Confidence varies by game state. Ensure frames are captured during active play, not loading screens.'],
        ].map(([prob, sol]) => (
          <div key={prob} style={{ padding: '8px 0', borderBottom: '1px solid var(--bg-border)', fontSize: 13 }}>
            <div style={{ color: 'var(--text-primary)', fontWeight: 500, marginBottom: 3 }}>{prob}</div>
            <div style={{ color: 'var(--text-secondary)' }}>{sol}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
