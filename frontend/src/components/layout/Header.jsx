import { useAuthStore } from '../../hooks/useAuth'
import { useSystemStatus } from '../../hooks/useSystemStatus'
import { FeaturedIcon } from '../ui/featured-icons'
import { Wifi, WifiOff, Loader } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { ThemeSwitch } from '../ui/theme-switch-button'

export default function Header() {
  const user    = useAuthStore((s) => s.user)
  const logout   = useAuthStore((s) => s.logout)
  const sys      = useSystemStatus()
  const navigate = useNavigate()

  // Derive display from live status
  const isChecking = sys.checking && sys.connected === null
  const isOnline   = sys.connected && sys.status === 'online'
  const isDegraded = sys.connected && sys.status === 'degraded'
  const isOffline  = !sys.connected && !isChecking

  const statusColor = isChecking ? 'gray' : isOnline ? 'success' : isDegraded ? 'warning' : 'error'
  const StatusIcon  = isChecking ? Loader  : isOnline || isDegraded ? Wifi : WifiOff
  const statusLabel = isChecking ? 'CHECKING...' : isOnline ? 'SYSTEM ONLINE' : isDegraded ? 'DEGRADED' : 'OFFLINE'
  const statusSub   = isOnline
    ? 'SVM v3 · Groq · RAG'
    : isDegraded
    ? 'Some components unavailable'
    : isOffline
    ? 'Cannot reach backend'
    : ''

  const labelColor  = isChecking ? '#52525b' : isOnline ? '#10B981' : isDegraded ? '#F59E0B' : '#EF4444'

  return (
    <header style={{
      background:     'rgba(2,3,5,0.85)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      borderBottom:   '1px solid rgba(255,255,255,.07)',
      position:       'sticky',
      top: 0,
      zIndex: 50,
    }}>
      <div style={{
        maxWidth: '960px', margin: '0 auto', padding: '0 24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        height: '58px',
      }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px', height: '32px', borderRadius: '8px',
            overflow: 'hidden', flexShrink: 0,
            boxShadow: '0 4px 14px rgba(99,102,241,.3)',
          }}>
            <img src="/logo.png" alt="ShieldGuard logo" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
          </div>
          <div>
            <div style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif",
              fontWeight: 800, fontSize: '17px', color: 'var(--text)', lineHeight: 1.1,
            }}>
              ShieldGuard
            </div>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '9px', color: 'var(--text-3)', letterSpacing: '1px', textTransform: 'uppercase',
            }}>
              Vishing Detection
            </div>
          </div>
        </div>

        {/* Right */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>

          {/* System status — live */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FeaturedIcon
              icon={StatusIcon}
              theme="outline"
              color={statusColor}
              size="md"
              style={isChecking ? { animation: 'spin 1.5s linear infinite' } : undefined}
            />
            <div>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: labelColor, letterSpacing: '0.5px', lineHeight: 1, transition: 'color .4s' }}>
                {statusLabel}
              </div>
              {statusSub && (
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '9px', color: 'var(--text-3)', letterSpacing: '0.5px', lineHeight: 1, marginTop: '3px' }}>
                  {statusSub}
                </div>
              )}
            </div>
          </div>

          {/* Divider */}
          <div style={{ width: '1px', height: '28px', background: 'var(--border)' }} />

          <ThemeSwitch />

          {/* Analytics link */}
          <button
            id="nav-analytics-btn"
            onClick={() => navigate('/admin')}
            style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: '9px',
              letterSpacing: '1.5px', textTransform: 'uppercase',
              color: '#6366F1', background: 'rgba(99,102,241,0.08)',
              border: '1px solid rgba(99,102,241,0.2)',
              borderRadius: '7px', padding: '5px 11px',
              cursor: 'pointer', transition: 'all .2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(99,102,241,0.18)'
              e.currentTarget.style.borderColor = 'rgba(99,102,241,0.45)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(99,102,241,0.08)'
              e.currentTarget.style.borderColor = 'rgba(99,102,241,0.2)'
            }}
          >
            Analytics
          </button>

          {/* User avatar chip */}
          {user && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                width: '30px', height: '30px', borderRadius: '50%',
                background: 'linear-gradient(135deg, #6366f1, #818cf8)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 700, fontSize: '12px', color: '#fff',
                flexShrink: 0, userSelect: 'none',
                boxShadow: '0 2px 8px rgba(99,102,241,.4)',
              }}>
                {user.username.charAt(0).toUpperCase()}
              </div>
              <span style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontSize: '13px', fontWeight: 600, color: 'var(--text)',
              }}>
                {user.username}
              </span>
            </div>
          )}

          {/* Sign out */}
          <button
            onClick={logout}
            style={{
              fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '12px', fontWeight: 500,
              color: 'var(--text-3)', background: 'transparent',
              border: '1px solid transparent',
              borderRadius: '8px', padding: '6px 12px',
              cursor: 'pointer', transition: 'all .2s', letterSpacing: '0.2px',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = '#EF4444'
              e.currentTarget.style.borderColor = 'rgba(239,68,68,.25)'
              e.currentTarget.style.background = 'rgba(239,68,68,.06)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-3)'
              e.currentTarget.style.borderColor = 'transparent'
              e.currentTarget.style.background = 'transparent'
            }}
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  )
}
