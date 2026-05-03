/**
 * src/pages/Sessions.tsx
 * Maturity: Working Prototype — filters, sorting, click-through to detail.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSessions, deleteSession } from '../services/api'
import type { Session } from '../services/api'

const GAMES     = ['All', 'Book of Dead', 'Gates of Olympus', 'Sweet Bonanza', 'Starburst', 'Wolf Gold']
const PLATFORMS = ['All', 'BetMGM', 'DraftKings', 'FanDuel', 'Bet365', 'PokerStars Casino']
const STATUSES  = ['All', 'complete', 'flagged', 'in_progress']

export default function Sessions() {
  const navigate = useNavigate()
  const [sessions,  setSessions]  = useState<Session[]>([])
  const [loading,   setLoading]   = useState(true)
  const [game,      setGame]      = useState('All')
  const [platform,  setPlatform]  = useState('All')
  const [status,    setStatus]    = useState('All')
  const [sortKey,   setSortKey]   = useState<keyof Session>('date')
  const [sortDesc,  setSortDesc]  = useState(true)
  const [deleting,  setDeleting]  = useState<number | null>(null)

  const fetch_ = async () => {
    setLoading(true)
    const params: any = {}
    if (game !== 'All')     params.game_name = game
    if (platform !== 'All') params.platform  = platform
    if (status !== 'All')   params.status    = status
    getSessions(params).then(setSessions).finally(() => setLoading(false))
  }

  useEffect(() => { fetch_() }, [game, platform, status])

  const sorted = [...sessions].sort((a, b) => {
    const av = a[sortKey] as any, bv = b[sortKey] as any
    if (av < bv) return sortDesc ? 1 : -1
    if (av > bv) return sortDesc ? -1 : 1
    return 0
  })

  const handleSort = (key: keyof Session) => {
    if (sortKey === key) setSortDesc(d => !d)
    else { setSortKey(key); setSortDesc(true) }
  }

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    if (!confirm('Delete this session and all its data?')) return
    setDeleting(id)
    await deleteSession(id)
    setSessions(prev => prev.filter(s => s.id !== id))
    setDeleting(null)
  }

  const sel = { background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '6px 10px', borderRadius: 'var(--radius-sm)', fontSize: 12, cursor: 'pointer' }
  const th   = (key: keyof Session, label: string) => (
    <th key={key} onClick={() => handleSort(key)}
      style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase', cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' }}>
      {label} {sortKey === key ? (sortDesc ? '↓' : '↑') : ''}
    </th>
  )

  return (
    <div style={{ padding: 'var(--page-margin)' }}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-6)' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Sessions</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{sessions.length} sessions</div>
        </div>
        <button onClick={fetch_}
          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '8px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>
          ↻ Refresh
        </button>
      </div>

      {/* ── Filters ────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 'var(--space-6)', flexWrap: 'wrap' }}>
        {[
          { label: 'Game',     value: game,     set: setGame,     opts: GAMES },
          { label: 'Platform', value: platform, set: setPlatform, opts: PLATFORMS },
          { label: 'Status',   value: status,   set: setStatus,   opts: STATUSES },
        ].map(({ label, value, set, opts }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{label}</span>
            <select value={value} onChange={e => set(e.target.value)} style={sel}>
              {opts.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          </div>
        ))}
        {(game !== 'All' || platform !== 'All' || status !== 'All') && (
          <button onClick={() => { setGame('All'); setPlatform('All'); setStatus('All') }}
            style={{ ...sel, color: 'var(--accent-blue)', borderColor: 'var(--accent-blue)' }}>
            Clear filters
          </button>
        )}
      </div>

      {/* ── Table ──────────────────────────────────────────────────────── */}
      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading…</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--bg-border)' }}>
                {th('date',          'Date')}
                {th('game_name',     'Game')}
                {th('platform',      'Platform')}
                {th('net_result',    'Net')}
                {th('rtp',           'RTP')}
                {th('spins',         'Spins')}
                {th('losing_streak', 'Streak')}
                {th('status',        'Status')}
                <th style={{ padding: '8px 12px', width: 60 }}></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(s => (
                <tr key={s.id}
                  onClick={() => navigate(`/sessions/${s.id}`)}
                  style={{ borderBottom: '1px solid var(--bg-border)', cursor: 'pointer', transition: 'background var(--transition-fast)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>{s.date}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-primary)', fontWeight: 500 }}>{s.game_name}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{s.platform}</td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: s.net_result >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {s.net_result >= 0 ? '+' : ''}${s.net_result.toFixed(2)}
                  </td>
                  <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: s.rtp < 85 ? 'var(--severity-critical)' : s.rtp < 96 ? 'var(--severity-warning)' : 'var(--text-secondary)' }}>
                    {s.rtp}%
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{s.spins.toLocaleString()}</td>
                  <td style={{ padding: '10px 12px', color: s.losing_streak > 15 ? 'var(--severity-critical)' : s.losing_streak > 8 ? 'var(--severity-warning)' : 'var(--text-muted)' }}>
                    {s.losing_streak}
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className={`badge badge-${s.status === 'flagged' ? 'warning' : 'success'}`}>{s.status}</span>
                  </td>
                  <td style={{ padding: '10px 12px' }}>
                    <button
                      onClick={e => handleDelete(e, s.id)}
                      disabled={deleting === s.id}
                      style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16, lineHeight: 1 }}
                      title="Delete session"
                    >
                      {deleting === s.id ? '…' : '×'}
                    </button>
                  </td>
                </tr>
              ))}
              {sorted.length === 0 && (
                <tr>
                  <td colSpan={9} style={{ padding: '32px 12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                    No sessions match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
