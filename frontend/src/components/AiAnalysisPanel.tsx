/**
 * src/components/AiAnalysisPanel.tsx
 * ------------------------------------
 * Displays Claude AI-powered session analysis.
 * Shows setup instructions when no API key configured.
 * Falls back gracefully to rule-based results.
 * Maturity: Working Prototype
 */

import { useState, useEffect } from 'react'
import { runAiAnalysis, getCachedAiAnalysis, getAiStatus } from '../services/api'
import type { AiAnalysis, AiStatus } from '../services/api'

const SEV_COLOR: Record<string, string> = {
  critical: 'var(--severity-critical)',
  warning:  'var(--severity-warning)',
  info:     'var(--accent-blue)',
}

const RISK_COLOR: Record<string, string> = {
  critical: 'var(--severity-critical)',
  high:     'var(--severity-critical)',
  moderate: 'var(--severity-warning)',
  low:      'var(--accent-green)',
}

const CAT_ICON: Record<string, string> = {
  rtp:        '📊',
  behaviour:  '🧠',
  discipline: '🎯',
  variance:   '📈',
  confidence: '🔍',
}

interface Props {
  sessionId: number
}

export function AiAnalysisPanel({ sessionId }: Props) {
  const [analysis,  setAnalysis]  = useState<AiAnalysis | null>(null)
  const [aiStatus,  setAiStatus]  = useState<AiStatus | null>(null)
  const [running,   setRunning]   = useState(false)
  const [loaded,    setLoaded]    = useState(false)
  const [error,     setError]     = useState('')

  useEffect(() => {
    // Load AI status and check for cached analysis
    Promise.all([
      getAiStatus(),
      getCachedAiAnalysis(sessionId).catch(() => null),
    ]).then(([status, cached]) => {
      setAiStatus(status)
      if (cached && !cached.error) setAnalysis(cached)
      setLoaded(true)
    })
  }, [sessionId])

  const run = async () => {
    setRunning(true); setError('')
    try {
      const result = await runAiAnalysis(sessionId)
      setAnalysis(result)
      if (result.error) setError(result.error)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Analysis failed.')
    } finally { setRunning(false) }
  }

  if (!loaded) return (
    <div style={{ padding: 24, color: 'var(--text-muted)', fontSize: 13 }}>Loading AI status…</div>
  )

  return (
    <div>
      {/* ── Header + run button ─────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 'var(--space-6)', borderColor: analysis?.ai_available ? 'var(--accent-blue)' : 'var(--bg-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ fontSize: 20 }}>🤖</span>
              <div style={{ fontWeight: 700, fontSize: 15 }}>Claude AI Analysis</div>
              {analysis?.model && (
                <span style={{ fontSize: 10, background: 'rgba(59,130,246,0.15)', color: 'var(--accent-blue)', padding: '2px 8px', borderRadius: 99, fontFamily: 'var(--font-mono)' }}>
                  {analysis.model}
                </span>
              )}
              {analysis?.source === 'rule_based' && (
                <span style={{ fontSize: 10, background: 'var(--bg-elevated)', color: 'var(--text-muted)', padding: '2px 8px', borderRadius: 99 }}>
                  rule-based
                </span>
              )}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {aiStatus?.available
                ? `Powered by ${aiStatus.model} · ~${aiStatus.cost_per_session} per analysis`
                : 'Add API key to enable AI-powered insights'}
            </div>
          </div>

          <button onClick={run} disabled={running}
            style={{
              background: running ? 'var(--bg-elevated)' : 'var(--accent-blue)',
              border: 'none', color: running ? 'var(--text-muted)' : '#fff',
              padding: '9px 20px', borderRadius: 'var(--radius-sm)',
              cursor: running ? 'not-allowed' : 'pointer',
              fontSize: 13, fontWeight: 600, flexShrink: 0,
            }}>
            {running ? '⏳ Analysing…' : analysis ? '↺ Re-run' : '▶ Run Analysis'}
          </button>
        </div>

        {/* API key setup instructions */}
        {!aiStatus?.available && (
          <div style={{ marginTop: 14, padding: '12px 14px', background: 'var(--bg-base)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--accent-blue)' }}>
            <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8, color: 'var(--accent-blue)' }}>
              Setup — 2 minutes
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              1. Get your free API key at{' '}
              <a href="https://console.anthropic.com" target="_blank" rel="noreferrer"
                style={{ color: 'var(--accent-blue)' }}>
                console.anthropic.com
              </a>
              <br />
              2. Set it in one of these ways:
            </div>
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[
                ['Windows (Command Prompt)', 'set ANTHROPIC_API_KEY=sk-ant-your-key-here'],
                ['Mac / Linux (Terminal)',   'export ANTHROPIC_API_KEY=sk-ant-your-key-here'],
                ['Config file',              'config/app_config.json → ai.anthropic_api_key'],
              ].map(([label, cmd]) => (
                <div key={label}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>{label}:</div>
                  <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11, background: 'var(--bg-elevated)', padding: '4px 8px', borderRadius: 4, color: 'var(--text-primary)', display: 'block' }}>
                    {cmd}
                  </code>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>
              3. Restart the backend. Pricing: ~$0.001–0.003 per session analysis.
            </div>
          </div>
        )}

        {error && (
          <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 'var(--radius-sm)', color: 'var(--severity-critical)', fontSize: 12 }}>
            {error}
          </div>
        )}
      </div>

      {/* ── Analysis results ─────────────────────────────────────────────────── */}
      {analysis && !analysis.error && (
        <>
          {/* Headline + verdict */}
          {analysis.headline && (
            <div className="card" style={{ marginBottom: 'var(--space-4)', borderColor: RISK_COLOR[analysis.risk_level ?? 'low'] }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
                    {analysis.headline}
                  </div>
                  {analysis.one_line_verdict && (
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      {analysis.one_line_verdict}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8, marginLeft: 16 }}>
                  <span style={{
                    background: RISK_COLOR[analysis.risk_level ?? 'low'] + '22',
                    color:      RISK_COLOR[analysis.risk_level ?? 'low'],
                    padding: '4px 12px', borderRadius: 99, fontSize: 11, fontWeight: 700,
                    textTransform: 'uppercase',
                  }}>
                    {analysis.risk_level} risk
                  </span>
                  {analysis.discipline_score != null && (
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>DISCIPLINE</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: analysis.discipline_score >= 70 ? 'var(--accent-green)' : analysis.discipline_score >= 45 ? 'var(--severity-warning)' : 'var(--severity-critical)' }}>
                        {analysis.discipline_score}<span style={{ fontSize: 11, color: 'var(--text-muted)' }}>/100</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Discipline bar */}
              {analysis.discipline_score != null && (
                <div style={{ background: 'var(--bg-base)', borderRadius: 4, height: 6 }}>
                  <div style={{
                    background: analysis.discipline_score >= 70 ? 'var(--accent-green)' : analysis.discipline_score >= 45 ? 'var(--severity-warning)' : 'var(--severity-critical)',
                    height: '100%', borderRadius: 4,
                    width: `${analysis.discipline_score}%`,
                    transition: 'width 0.6s ease',
                  }} />
                </div>
              )}
            </div>
          )}

          {/* AI Insights */}
          {analysis.insights?.length > 0 && (
            <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>Insights ({analysis.insights.length})</div>
              {analysis.insights.map((ins, i) => (
                <div key={i} style={{ display: 'flex', gap: 12, padding: '10px 0', borderBottom: i < analysis.insights.length - 1 ? '1px solid var(--bg-border)' : 'none' }}>
                  <div style={{ fontSize: 16, flexShrink: 0 }}>{CAT_ICON[ins.category] ?? '📌'}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                      <span className={`badge badge-${ins.severity}`}>{ins.severity}</span>
                      {ins.category && <span style={{ fontSize: 10, color: 'var(--text-muted)', alignSelf: 'center' }}>{ins.category}</span>}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{ins.text}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Behaviour summary */}
          {analysis.behaviour_summary && (
            <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Behaviour Summary</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8 }}>{analysis.behaviour_summary}</div>
            </div>
          )}

          {/* Notable moments */}
          {analysis.notable_moments?.length > 0 && (
            <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Notable Moments</div>
              {analysis.notable_moments.map((m, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '6px 0', borderBottom: i < analysis.notable_moments!.length - 1 ? '1px solid var(--bg-border)' : 'none', lineHeight: 1.6 }}>
                  ▶ {m}
                </div>
              ))}
            </div>
          )}

          {/* Meta */}
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'right' }}>
            {analysis.source === 'claude_ai' && analysis.generated_at
              ? `Analysed by ${analysis.model} · ${new Date(analysis.generated_at).toLocaleString()}`
              : analysis.source === 'rule_based'
              ? 'Rule-based analysis · Add ANTHROPIC_API_KEY for Claude AI'
              : ''}
          </div>
        </>
      )}

      {/* No analysis yet */}
      {!analysis && !running && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, color: 'var(--text-muted)', gap: 12 }}>
          <div style={{ fontSize: 40 }}>🤖</div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>No analysis yet</div>
          <div style={{ fontSize: 12, textAlign: 'center', maxWidth: 320 }}>
            {aiStatus?.available
              ? 'Click "Run Analysis" to get Claude AI-powered insights for this session.'
              : 'Configure your API key above, then click "Run Analysis".'}
          </div>
        </div>
      )}
    </div>
  )
}
