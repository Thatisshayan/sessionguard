/**
 * src/pages/ProfileEditor.tsx
 * ----------------------------
 * Visual ROI coordinate editor for OCR profiles.
 * Set balance/bet/win regions, preview config, test with sample frame.
 * Maturity: Working Prototype
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import { getProfiles } from '../services/api'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

interface Region { x: number; y: number; w: number; h: number }
interface RoiConfig {
  balance_region: [number,number,number,number]
  bet_region:     [number,number,number,number]
  win_region:     [number,number,number,number]
  scale:          number
  threshold:      number | null
}

const REGION_COLORS = {
  balance_region: { bg: 'rgba(59,130,246,0.25)',  border: '#3b82f6', label: 'Balance' },
  bet_region:     { bg: 'rgba(245,158,11,0.25)',  border: '#f59e0b', label: 'Bet'     },
  win_region:     { bg: 'rgba(34,197,94,0.25)',   border: '#22c55e', label: 'Win'     },
}

const numInput = (value: number, onChange: (v: number) => void, label: string) => (
  <div>
    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3, textTransform: 'uppercase' }}>{label}</div>
    <input type="number" value={value} min={0} max={9999}
      onChange={e => onChange(Number(e.target.value))}
      style={{
        width: 70, background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
        color: 'var(--text-primary)', padding: '6px 8px', borderRadius: 'var(--radius-sm)', fontSize: 13,
      }} />
  </div>
)

export default function ProfileEditor() {
  const { id }     = useParams<{ id: string }>()
  const navigate   = useNavigate()
  const isNew      = id === 'new'

  const [name,     setName]     = useState('')
  const [gameName, setGameName] = useState('')
  const [platform, setPlatform] = useState('')
  const [roi,      setRoi]      = useState<RoiConfig>({
    balance_region: [10, 10, 200, 50],
    bet_region:     [10, 70, 150, 40],
    win_region:     [10, 120, 200, 50],
    scale: 2.0, threshold: null,
  })
  const [alertRules, setAlertRules] = useState({
    rtp_warning: 96, rtp_critical: 85, max_loss: 200, streak_warning: 8, streak_critical: 15,
  })
  const [saving,   setSaving]   = useState(false)
  const [error,    setError]    = useState('')
  const [success,  setSuccess]  = useState('')

  useEffect(() => {
    if (!isNew && id) {
      axios.get(`${BASE}/profiles/${id}`).then(res => {
        const p = res.data
        setName(p.name); setGameName(p.game_name); setPlatform(p.platform)
        if (p.roi_config?.balance_region) setRoi({ ...roi, ...p.roi_config })
        if (p.alert_rules?.rtp_warning) setAlertRules({ ...alertRules, ...p.alert_rules })
      }).catch(() => navigate('/profiles'))
    }
  }, [id])

  const updateRegion = (key: keyof typeof REGION_COLORS, field: 'x'|'y'|'w'|'h', val: number) => {
    const idx = { x:0, y:1, w:2, h:3 }[field]
    const arr = [...roi[key as keyof RoiConfig] as [number,number,number,number]] as [number,number,number,number]
    arr[idx]  = val
    setRoi(r => ({ ...r, [key]: arr }))
  }

  const save = async () => {
    if (!name || !gameName || !platform) { setError('Name, Game, and Platform are required.'); return }
    setSaving(true); setError(''); setSuccess('')
    const payload = {
      name, game_name: gameName, platform,
      roi_config:  roi,
      alert_rules: alertRules,
    }
    try {
      if (isNew) {
        await axios.post(`${BASE}/profiles`, payload)
      } else {
        // patch — use delete+create for simplicity since no PATCH on profiles
        await axios.delete(`${BASE}/profiles/${id}`)
        await axios.post(`${BASE}/profiles`, payload)
      }
      setSuccess('Profile saved.')
      setTimeout(() => navigate('/profiles'), 1200)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Save failed.')
    } finally { setSaving(false) }
  }

  const inp: React.CSSProperties = {
    background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
    color: 'var(--text-primary)', padding: '8px 12px', borderRadius: 'var(--radius-sm)',
    fontSize: 13, width: '100%',
  }

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 900 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 'var(--space-8)' }}>
        <button onClick={() => navigate('/profiles')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 13 }}>← Profiles</button>
        <span style={{ color: 'var(--bg-border)' }}>/</span>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>{isNew ? 'New Profile' : 'Edit Profile'}</h1>
      </div>

      {/* Basic info */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>Profile Info</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          {[['Profile Name','e.g. Book of Dead — BetMGM', name, setName],
            ['Game Name',   'e.g. Book of Dead',          gameName, setGameName],
            ['Platform',    'e.g. BetMGM',                platform, setPlatform],
          ].map(([label, placeholder, val, setter]) => (
            <div key={label as string}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>{label as string}</div>
              <input style={inp} value={val as string} placeholder={placeholder as string}
                onChange={e => (setter as (v: string) => void)(e.target.value)} />
            </div>
          ))}
        </div>
      </div>

      {/* ROI Config */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>OCR Region of Interest (ROI)</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.7 }}>
          Set pixel coordinates for each field region on the game screenshot.
          <strong style={{ color: 'var(--text-secondary)' }}> [x, y, width, height]</strong> — 
          x/y = top-left corner of the region. Scale 2.0 = double resolution before OCR (recommended).
          Use the Parser Benchmark page to test accuracy.
        </div>

        {/* Visual preview box */}
        <div style={{
          position: 'relative', background: 'var(--bg-base)', border: '1px solid var(--bg-border)',
          borderRadius: 'var(--radius-sm)', height: 200, marginBottom: 20, overflow: 'hidden',
        }}>
          <div style={{ position: 'absolute', top: 8, left: 8, fontSize: 10, color: 'var(--text-muted)' }}>
            Preview (not to scale — illustrative only)
          </div>
          {(Object.entries(REGION_COLORS) as [keyof typeof REGION_COLORS, typeof REGION_COLORS[keyof typeof REGION_COLORS]][]).map(([key, style]) => {
            const r = roi[key]
            const scale = 0.3
            return (
              <div key={key} style={{
                position: 'absolute',
                left:   r[0] * scale, top:    r[1] * scale + 20,
                width:  r[2] * scale, height: r[3] * scale,
                background: style.bg, border: `2px solid ${style.border}`,
                borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{ fontSize: 9, fontWeight: 600, color: style.border }}>{style.label}</span>
              </div>
            )
          })}
        </div>

        {/* Region controls */}
        {(Object.entries(REGION_COLORS) as [keyof typeof REGION_COLORS, typeof REGION_COLORS[keyof typeof REGION_COLORS]][]).map(([key, style]) => (
          <div key={key} style={{ marginBottom: 16, padding: '12px 14px', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', borderLeft: `3px solid ${style.border}` }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: style.border, marginBottom: 10 }}>{style.label} Region</div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {(['x','y','w','h'] as const).map(field => (
                numInput(roi[key][{x:0,y:1,w:2,h:3}[field]], v => updateRegion(key, field, v), field.toUpperCase())
              ))}
              <div style={{ color: 'var(--text-muted)', fontSize: 11, alignSelf: 'flex-end', paddingBottom: 6 }}>
                px from top-left
              </div>
            </div>
          </div>
        ))}

        {/* Scale + threshold */}
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Scale (recommend 2.0)</div>
            <input type="number" step="0.5" min="1" max="4" value={roi.scale}
              onChange={e => setRoi(r => ({ ...r, scale: Number(e.target.value) }))}
              style={{ ...inp, width: 100 }} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>Threshold (0–255, blank=none)</div>
            <input type="number" min="0" max="255"
              value={roi.threshold ?? ''}
              placeholder="none"
              onChange={e => setRoi(r => ({ ...r, threshold: e.target.value ? Number(e.target.value) : null }))}
              style={{ ...inp, width: 100 }} />
          </div>
        </div>
      </div>

      {/* Alert rules */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>Alert Thresholds</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {[
            ['rtp_warning',     'RTP Warning %'],
            ['rtp_critical',    'RTP Critical %'],
            ['max_loss',        'Max Loss $'],
            ['streak_warning',  'Streak Warning'],
            ['streak_critical', 'Streak Critical'],
          ].map(([key, label]) => (
            <div key={key}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>{label}</div>
              <input type="number" value={(alertRules as any)[key]}
                onChange={e => setAlertRules(r => ({ ...r, [key]: Number(e.target.value) }))}
                style={{ ...inp }} />
            </div>
          ))}
        </div>
      </div>

      {/* Save */}
      {error   && <div style={{ marginBottom: 12, color: 'var(--severity-critical)', fontSize: 13 }}>{error}</div>}
      {success && <div style={{ marginBottom: 12, color: 'var(--accent-green)',      fontSize: 13 }}>✓ {success}</div>}
      <div style={{ display: 'flex', gap: 12 }}>
        <button onClick={save} disabled={saving}
          style={{ background: 'var(--accent-blue)', border: 'none', color: '#fff', padding: '10px 28px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 14, fontWeight: 600 }}>
          {saving ? 'Saving…' : 'Save Profile'}
        </button>
        <button onClick={() => navigate('/profiles')}
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '10px 20px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>
          Cancel
        </button>
      </div>
    </div>
  )
}
