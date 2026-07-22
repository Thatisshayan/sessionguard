/**
 * src/pages/SessionDetail.tsx
 * ----------------------------
 * Full session deep-dive. Composes tab sub-components from
 * src/components/session-detail/*; data layer is React Query
 * (see useSessionDetailData) — deduped, cached, background-refetched.
 *
 * Maturity: Working Prototype
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useSessionDetailData } from '../components/session-detail/useSessionDetailData'
import { KPI, money, pct, col, sevCol } from '../components/session-detail/shared'
import { OverviewTab } from '../components/session-detail/OverviewTab'
import { EventsTab } from '../components/session-detail/EventsTab'
import { BehaviorTab } from '../components/session-detail/BehaviorTab'
import { ReviewTab } from '../components/session-detail/ReviewTab'
import { ExportsTab } from '../components/session-detail/ExportsTab'
import { AiAnalysisPanel } from '../components/AiAnalysisPanel'

type Tab = 'overview' | 'events' | 'behavior' | 'review' | 'exports' | 'ai'

export default function SessionDetail() {
  const { id }    = useParams<{ id: string }>()
  const navigate  = useNavigate()
  const sessionId = Number(id)
  const [activeTab, setActiveTab] = useState<Tab>('overview')

  const {
    session, insights, alerts, queue, events, evSummary, behavior, exports,
    loading, error, acknowledge, resolve, createExport, exporting, startLive, stopLive,
  } = useSessionDetailData(sessionId)

  const [liveRun, setLiveRun] = useState<any>(null)
  const handleStartLive = async () => setLiveRun(await startLive())
  const handleStopLive  = async () => { if (liveRun) { await stopLive(liveRun.id); setLiveRun(null) } }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
      Loading session…
    </div>
  )

  if (error || !session) return (
    <div style={{ padding: 'var(--page-margin)' }}>
      <div className="card" style={{ borderColor: 'var(--severity-critical)', maxWidth: 500 }}>
        <div style={{ color: 'var(--severity-critical)', fontWeight: 600, marginBottom: 8 }}>Failed to load session</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{error}</div>
        <button onClick={() => navigate('/sessions')} style={{ marginTop: 12, background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', color: 'var(--text-secondary)', padding: '6px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 13 }}>← Sessions</button>
      </div>
    </div>
  )

  const rtpColor    = session.rtp < 85 ? 'var(--severity-critical)' : session.rtp < 96 ? 'var(--severity-warning)' : 'var(--accent-blue)'
  const streakColor = session.losing_streak > 15 ? 'var(--severity-critical)' : session.losing_streak > 8 ? 'var(--severity-warning)' : 'var(--text-primary)'

  const TAB_BTN = (key: Tab, label: string, count?: number) => (
    <button key={key} onClick={() => setActiveTab(key)}
      style={{
        background: activeTab === key ? 'var(--accent-blue)' : 'var(--bg-elevated)',
        border: `1px solid ${activeTab === key ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
        color: activeTab === key ? '#fff' : 'var(--text-secondary)',
        padding: '6px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 500,
      }}>
      {label}{count != null && count > 0 ? ` (${count})` : ''}
    </button>
  )

  return (
    <div style={{ padding: 'var(--page-margin)', maxWidth: 'var(--content-max-width)', margin: '0 auto' }}>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 'var(--space-4)', fontSize: 13 }}>
        <button onClick={() => navigate('/sessions')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}>← Sessions</button>
        <span style={{ color: 'var(--bg-border)' }}>/</span>
        <span style={{ color: 'var(--text-secondary)' }}>{session.name}</span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-6)' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>{session.name}</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            {session.game_name} · {session.platform} · {session.date} · {session.duration_minutes} min
            {events.length > 0 && <span style={{ marginLeft: 12, color: 'var(--accent-blue)' }}>{events.length} events</span>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {liveRun ? (
            <button onClick={handleStopLive} style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid var(--severity-critical)', color: 'var(--severity-critical)', padding: '7px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              ⏹ Stop Live
            </button>
          ) : (
            <button onClick={handleStartLive} style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid var(--accent-green)', color: 'var(--accent-green)', padding: '7px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              ▶ Start Live
            </button>
          )}
          <span className={`badge badge-${session.status === 'flagged' ? 'warning' : 'success'}`}>{session.status}</span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 'var(--gutter)', marginBottom: 'var(--space-6)', flexWrap: 'wrap' }}>
        <KPI label="Net Result"     value={money(session.net_result)}      accent={col(session.net_result)} />
        <KPI label="RTP"            value={pct(session.rtp)}               accent={rtpColor} />
        <KPI label="Spins"          value={session.spins.toLocaleString()} />
        <KPI label="Total Wagered"  value={`$${session.total_bets.toFixed(2)}`} />
        <KPI label="Total Returned" value={`$${session.total_wins.toFixed(2)}`} />
        <KPI label="Biggest Win"    value={`$${session.biggest_win.toFixed(2)}`} accent="var(--accent-green)" />
        <KPI label="Losing Streak"  value={`${session.losing_streak}`}         accent={streakColor} />
        {evSummary && <KPI label="Win Rate"    value={`${evSummary.win_rate_pct}%`} />}
        {evSummary && <KPI label="Avg Bet"     value={`$${evSummary.avg_bet}`} />}
        {behavior   && <KPI label="Risk Score" value={`${behavior.risk_score}/100`} accent={sevCol[behavior.risk_level] ?? 'var(--text-primary)'} />}
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-6)' }}>
        {TAB_BTN('overview',  'Overview')}
        {TAB_BTN('events',    'Event Timeline', events.length)}
        {TAB_BTN('behavior',  'Behavior')}
        {TAB_BTN('review',    'Review Queue', queue.length)}
        {TAB_BTN('exports',   'Exports')}{TAB_BTN('ai', 'AI Analysis 🤖')}
      </div>

      {activeTab === 'overview' && <OverviewTab session={session} events={events} insights={insights} alerts={alerts} onAck={acknowledge} />}
      {activeTab === 'events'   && <EventsTab events={events} evSummary={evSummary} />}
      {activeTab === 'behavior' && <BehaviorTab behavior={behavior} />}
      {activeTab === 'review'   && <ReviewTab queue={queue} onResolve={resolve} />}
      {activeTab === 'ai'       && <AiAnalysisPanel sessionId={sessionId} />}
      {activeTab === 'exports'  && <ExportsTab exports_={exports} exporting={exporting} onExport={createExport} />}
    </div>
  )
}
