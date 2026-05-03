/**
 * src/components/LiveCoach.tsx
 * AI Live Coach - boxing corner man for live sessions.
 * Polls /coach/{run_id} every 15s. Shows coaching messages.
 */

import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { playCoachSound } from '../utils/coachSounds'

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

interface CoachMsg {
  type: 'tip' | 'warning' | 'critical' | 'positive' | 'neutral'
  message: string; trigger: string; source: 'claude' | 'rule'; timestamp: number
}
interface Props { runId: number | null; running: boolean; style?: 'strict' | 'balanced' | 'supportive' }

const TYPE_STYLE: Record<string, { bg: string; border: string; icon: string; label: string }> = {
  critical: { bg:'rgba(239,68,68,0.08)',  border:'#ef4444', icon:'🛑', label:'CRITICAL' },
  warning:  { bg:'rgba(245,158,11,0.08)', border:'#f59e0b', icon:'⚠️', label:'WARNING'  },
  positive: { bg:'rgba(34,197,94,0.08)',  border:'#22c55e', icon:'✅', label:'GOOD'     },
  tip:      { bg:'rgba(59,130,246,0.08)', border:'#3b82f6', icon:'💡', label:'TIP'      },
  neutral:  { bg:'rgba(139,146,164,0.08)',border:'#8892a4', icon:'ℹ',  label:'INFO'     },
}

export default function LiveCoach({ runId, running, style = 'balanced' }: Props) {
  const [messages, setMessages] = useState<CoachMsg[]>([])
  const [aiActive, setAiActive] = useState(false)
  const [expanded, setExpanded] = useState(true)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    axios.get(`${BASE}/coach-status`).then(r => setAiActive(r.data.ai_available)).catch(() => {})
  }, [])

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    if (!running || !runId) return
    axios.post(`${BASE}/coach/${runId}/reset`).catch(() => {})
    pollRef.current = setInterval(() => {
      axios.get(`${BASE}/coach/${runId}?style=${style}`).then(res => {
        const msg = res.data.message
        if (msg) {
            playCoachSound(msg.type)
            setMessages(prev => [{...msg, id: Date.now()}, ...prev].slice(0, 20))
          }
      }).catch(() => {})
    }, 15000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [running, runId, style])

  const latest = messages[0]
  const ls     = latest ? (TYPE_STYLE[latest.type] ?? TYPE_STYLE.neutral) : null

  return (
    <div style={{ background:'var(--bg-surface)', border:'1px solid var(--bg-border)', borderRadius:'var(--radius-md)', overflow:'hidden' }}>
      <div onClick={() => setExpanded(e => !e)} style={{ padding:'12px 14px', borderBottom: expanded?'1px solid var(--bg-border)':'none', display:'flex', alignItems:'center', gap:10, cursor:'pointer', userSelect:'none' }}>
        <span style={{ fontSize:18 }}>🥊</span>
        <div style={{ flex:1 }}>
          <div style={{ fontSize:13, fontWeight:700, color:'var(--text-primary)' }}>
            Live Coach
            {aiActive && <span style={{ marginLeft:8, fontSize:9, fontWeight:600, background:'rgba(59,130,246,0.15)', color:'#3b82f6', padding:'2px 6px', borderRadius:4, textTransform:'uppercase' }}>Claude AI</span>}
          </div>
          <div style={{ fontSize:10, color:'var(--text-muted)', marginTop:2 }}>
            {running ? `${aiActive?'AI':'Rule-based'} coaching active — ${style}` : 'Start a session to activate coaching'}
          </div>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          {running && <div style={{ width:7, height:7, borderRadius:'50%', background:'var(--accent-green)' }} />}
          <span style={{ fontSize:12, color:'var(--text-muted)' }}>{expanded?'▲':'▼'}</span>
        </div>
      </div>

      {expanded && (
        <div>
          {latest && ls ? (
            <div style={{ margin:12, padding:'14px 16px', background:ls.bg, border:`2px solid ${ls.border}`, borderRadius:'var(--radius-sm)' }}>
              <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:8 }}>
                <span style={{ fontSize:20 }}>{ls.icon}</span>
                <span style={{ fontSize:10, fontWeight:700, color:ls.border, textTransform:'uppercase', letterSpacing:'0.06em' }}>{ls.label}</span>
                <span style={{ fontSize:10, color:'var(--text-muted)', marginLeft:'auto' }}>{latest.source==='claude'?'🤖 Claude':'📋 Rule'}</span>
              </div>
              <div style={{ fontSize:13, color:'var(--text-primary)', lineHeight:1.7, fontWeight:500 }}>{latest.message}</div>
            </div>
          ) : (
            <div style={{ padding:'24px 16px', textAlign:'center', color:'var(--text-muted)', fontSize:12 }}>
              {running ? '👀 Watching your session… coach fires every ~15 spins or when a pattern is detected' : '🥊 Coach appears here when your session is running'}
            </div>
          )}

          {messages.length > 1 && (
            <div style={{ padding:'0 12px 12px' }}>
              <div style={{ fontSize:10, color:'var(--text-muted)', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:6 }}>Session log</div>
              <div style={{ maxHeight:160, overflowY:'auto' }}>
                {messages.slice(1).map((m, i) => {
                  const s = TYPE_STYLE[m.type] ?? TYPE_STYLE.neutral
                  return <div key={i} style={{ padding:'7px 10px', marginBottom:4, background:'var(--bg-elevated)', borderRadius:'var(--radius-sm)', borderLeft:`3px solid ${s.border}`, fontSize:11, color:'var(--text-secondary)', lineHeight:1.5 }}><span style={{ marginRight:6 }}>{s.icon}</span>{m.message}</div>
                })}
              </div>
            </div>
          )}

          {!running && (
            <div style={{ padding:'0 12px 12px', fontSize:11, color:'var(--text-muted)', lineHeight:1.7 }}>
              <strong style={{ color:'var(--text-secondary)' }}>Coaching styles:</strong><br/>
              🔴 <strong>Strict</strong> — direct, no sugar-coating<br/>
              🟡 <strong>Balanced</strong> — honest but calm<br/>
              🟢 <strong>Supportive</strong> — patient and encouraging
            </div>
          )}
        </div>
      )}
    </div>
  )
}
