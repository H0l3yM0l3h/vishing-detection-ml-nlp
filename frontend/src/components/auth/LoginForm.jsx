import { useState } from 'react'
import { useAuthStore } from '../../hooks/useAuth'

const inputStyle = {
  width: '100%', background: 'rgba(5,11,24,.6)',
  border: '1px solid rgba(255,255,255,.1)', borderRadius: '10px',
  padding: '11px 16px', color: '#F0F6FF',
  fontFamily: "'Outfit', sans-serif", fontSize: '15px', outline: 'none',
  transition: 'border-color .2s, box-shadow .2s',
}

function Field({ label, ...props }) {
  const [focused, setFocused] = useState(false)
  return (
    <div>
      <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500, color: '#94A3B8', fontFamily: "'Outfit', sans-serif" }}>
        {label}
      </label>
      <input
        {...props}
        style={{
          ...inputStyle,
          borderColor: focused ? 'rgba(99,102,241,.6)' : 'rgba(255,255,255,.1)',
          boxShadow:   focused ? '0 0 0 3px rgba(99,102,241,.12)' : 'none',
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
    </div>
  )
}

export default function LoginForm({ onSwitchToRegister }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, loading, error } = useAuthStore()
  const [lockInfo, setLockInfo]   = useState(null)
  const [remaining, setRemaining] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const res = await login(username.trim(), password)
    if (!res.success) {
      if (res.locked)                           setLockInfo({ minutes: res.minutes_remaining })
      if (res.remaining_attempts !== undefined) setRemaining(res.remaining_attempts)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ marginBottom: '4px' }}>
        <h2 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: '22px', color: '#F0F6FF', marginBottom: '4px' }}>
          Welcome back
        </h2>
        <p style={{ fontFamily: "'Outfit', sans-serif", fontSize: '14px', color: '#94A3B8' }}>
          Sign in to your ShieldGuard account
        </p>
      </div>

      {lockInfo && (
        <div style={{ background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', borderRadius: '10px', padding: '14px', textAlign: 'center' }}>
          <div style={{ fontWeight: 700, color: '#FCA5A5', marginBottom: '4px' }}>Account Locked</div>
          <div style={{ fontSize: '13px', color: '#94A3B8' }}>Try again in {lockInfo.minutes} minute{lockInfo.minutes !== 1 ? 's' : ''}</div>
        </div>
      )}

      {error && !lockInfo && (
        <div style={{ background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.25)', borderRadius: '10px', padding: '12px 16px' }}>
          <span style={{ fontSize: '14px', color: '#FCA5A5' }}>{error}</span>
          {remaining !== null && <span style={{ fontSize: '12px', color: '#94A3B8', marginLeft: '10px' }}>({remaining} attempts left)</span>}
        </div>
      )}

      <Field label="Username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter your username" autoComplete="username" required />
      <Field label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" autoComplete="current-password" required />

      <button type="submit" disabled={loading} style={{
        width: '100%', padding: '13px', borderRadius: '10px', border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
        background: loading ? '#374151' : 'linear-gradient(135deg, #6366F1, #818CF8)',
        color: '#fff', fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: '16px',
        boxShadow: loading ? 'none' : '0 4px 20px rgba(99,102,241,.35)', transition: 'opacity .2s, transform .1s',
        opacity: loading ? 0.6 : 1,
      }}
        onMouseEnter={(e) => { if (!loading) e.target.style.transform = 'translateY(-1px)' }}
        onMouseLeave={(e) => { e.target.style.transform = 'translateY(0)' }}
      >
        {loading ? 'Signing in...' : 'Sign In'}
      </button>

      <div style={{ textAlign: 'center', paddingTop: '4px' }}>
        <button type="button" onClick={onSwitchToRegister}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Outfit', sans-serif", fontSize: '14px', color: '#818CF8', transition: 'color .15s' }}
          onMouseEnter={(e) => { e.target.style.color = '#A5B4FC' }}
          onMouseLeave={(e) => { e.target.style.color = '#818CF8' }}
        >
          Don't have an account? <strong>Create one</strong>
        </button>
      </div>
    </form>
  )
}
