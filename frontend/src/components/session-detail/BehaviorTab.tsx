/**
 * src/components/session-detail/BehaviorTab.tsx
 * -------------------------------------------------
 * Behavior risk score + pattern cards + key findings.
 */

import { SevBadge, sevCol } from './shared'

export function BehaviorTab({ behavior }: { behavior: any }) {
  if (!behavior) {
    return (
      <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
        Behavior analysis unavailable — need at least 3 events.
      </div>
    )
  }

  return (
    <>
      <div className="card" style={{ marginBottom: 'var(--space-6)', borderColor: sevCol[behavior.risk_level] ?? 'var(--bg-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Behavior Risk Assessment</div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 700, color: sevCol[behavior.risk_level] }}>
            {behavior.risk_score}<span style={{ fontSize: 13, color: 'var(--text-muted)' }}>/100</span>
          </span>
        </div>
        <div style={{ background: 'var(--bg-base)', borderRadius: 4, height: 6, marginBottom: 12 }}>
          <div style={{ background: sevCol[behavior.risk_level], height: '100%', borderRadius: 4, width: `${behavior.risk_score}%`, transition: 'width 0.5s ease' }} />
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{behavior.summary}</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gutter)', marginBottom: 'var(--space-6)' }}>
        {Object.entries(behavior.patterns).map(([key, pattern]: [string, any]) => (
          <div key={key} className="card" style={{ borderColor: pattern.detected ? (sevCol[pattern.severity] ?? 'var(--bg-border)') : 'var(--bg-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                {key.replace(/_/g, ' ')}
              </div>
              {pattern.detected
                ? <SevBadge sev={pattern.severity} />
                : <span className="badge badge-success">clear</span>
              }
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{pattern.detail}</div>
            {pattern.slope != null && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
                slope={pattern.slope} {pattern.escalation_ratio != null && `| ratio=${pattern.escalation_ratio}x`}
              </div>
            )}
            {pattern.max_streak != null && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
                max streak={pattern.max_streak} | clusters={pattern.clusters?.length ?? 0}
              </div>
            )}
            {pattern.peak_volatility != null && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, fontFamily: 'var(--font-mono)' }}>
                peak vol=${pattern.peak_volatility} | zones={pattern.zones?.length ?? 0}
              </div>
            )}
          </div>
        ))}
      </div>

      {behavior.findings.length > 0 && (
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Key Findings</div>
          {behavior.findings.map((f: string, i: number) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '8px 0', borderBottom: '1px solid var(--bg-border)', lineHeight: 1.6 }}>
              ▶ {f}
            </div>
          ))}
        </div>
      )}
    </>
  )
}
