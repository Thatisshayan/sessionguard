import { Component, ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          height: '100vh', background: 'var(--bg-base)', color: 'var(--text-primary)',
          flexDirection: 'column', gap: 16, padding: 32, textAlign: 'center',
        }}>
          <div style={{ fontSize: 32 }}>⚠️</div>
          <h2 style={{ fontSize: 18, fontWeight: 700 }}>Something went wrong</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, maxWidth: 400 }}>
            {this.state.error?.message || 'An unexpected error occurred.'}
          </p>
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}
            style={{
              background: 'var(--accent-blue)', border: 'none', color: '#fff',
              padding: '10px 24px', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
              fontSize: 13, fontWeight: 600,
            }}>
            Reload page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
