import { Component } from 'react'

/**
 * Top-level error boundary.
 *
 * The app had none, so a single render-time throw blanked the entire page with
 * no message and no way back. That is reachable in practice: AdminDashboard
 * calls .toLocaleString() and .length on analytics fields without guarding
 * them, so a partial payload took the whole UI down.
 *
 * React only recovers from render errors via a class component, so this stays
 * a class even though the rest of the codebase is hooks-based.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Kept in the console rather than shown to the user: stack traces can
    // disclose internal structure, and they mean nothing to a non-technical
    // person looking at a fraud-detection tool.
    console.error('[ShieldGuard] Unhandled UI error:', error, info?.componentStack)
  }

  handleReload = () => {
    this.setState({ error: null })
    window.location.reload()
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div
        role="alert"
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          background: 'var(--bg)',
          fontFamily: "'Plus Jakarta Sans', sans-serif",
        }}
      >
        <div style={{ maxWidth: 460, textAlign: 'center' }}>
          <div
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: 'var(--red)',
              marginBottom: 12,
            }}
          >
            Interface error
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)', margin: '0 0 10px' }}>
            Something went wrong on this screen
          </h1>
          <p style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--text-2)', margin: '0 0 22px' }}>
            Your session and your scan history are unaffected. Reloading usually clears this.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            style={{
              padding: '10px 22px',
              borderRadius: 8,
              border: '1px solid var(--border-hi)',
              background: 'var(--surface-2)',
              color: 'var(--text)',
              fontSize: 14,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Reload ShieldGuard
          </button>
        </div>
      </div>
    )
  }
}
