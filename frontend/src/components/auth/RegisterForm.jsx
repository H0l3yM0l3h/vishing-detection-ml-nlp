import { useState } from 'react'
import { useAuthStore } from '../../hooks/useAuth'

const RULES = [
  { label: 'At least 12 characters',    test: (p) => p.length >= 12 },
  { label: 'One uppercase letter',       test: (p) => /[A-Z]/.test(p) },
  { label: 'One lowercase letter',       test: (p) => /[a-z]/.test(p) },
  { label: 'One number',                 test: (p) => /\d/.test(p) },
  { label: 'One special character',      test: (p) => /[^A-Za-z0-9]/.test(p) },
]

const inputBase = {
  width: '100%', background: 'rgba(5,11,24,.6)',
  border: '1px solid rgba(255,255,255,.1)', borderRadius: '10px',
  padding: '11px 16px', color: '#F0F6FF',
  fontFamily: "'Outfit', sans-serif", fontSize: '15px', outline: 'none',
  transition: 'border-color .2s, box-shadow .2s',
}

function Field({ label, error: fieldError, ...props }) {
  const [focused, setFocused] = useState(false)
  return (
    <div>
      <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500, color: '#94A3B8', fontFamily: "'Outfit', sans-serif" }}>{label}</label>
      <input {...props}
        style={{ ...inputBase, borderColor: fieldError ? 'rgba(239,68,68,.5)' : focused ? 'rgba(99,102,241,.6)' : 'rgba(255,255,255,.1)', boxShadow: focused ? '0 0 0 3px rgba(99,102,241,.12)' : 'none' }}
        onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
      />
      {fieldError && <p style={{ fontSize: '12px', color: '#FCA5A5', marginTop: '4px', fontFamily: "'Outfit', sans-serif" }}>{fieldError}</p>}
    </div>
  )
}

export default function RegisterForm({ onSwitchToLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm,  setConfirm]  = useState('')
  const { register, loading, error } = useAuthStore()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password !== confirm) return
    await register(username, password)
  }

  const allPassed     = RULES.every((r) => r.test(password))
  const passwordsMatch = password && confirm && password === confirm

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      <div style={{ marginBottom: '4px' }}>
        <h2 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: '22px', color: '#F0F6FF', marginBottom: '4px' }}>Create account</h2>
        <p style={{ fontFamily: "'Outfit', sans-serif", fontSize: '14px', color: '#94A3B8' }}>Get started with ShieldGuard</p>
      </div>

      {error && (
        <div style={{ background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.25)', borderRadius: '10px', padding: '12px 16px' }}>
          <span style={{ fontSize: '14px', color: '#FCA5A5', fontFamily: "'Outfit', sans-serif" }}>{error}</span>
        </div>
      )}

      <Field label="Username" type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="3-32 chars, letters, numbers, underscores" autoComplete="username" required />
      <Field label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a strong password" autoComplete="new-password" required />

      {/* Rules */}
      {password.length > 0 && (
        <div style={{ background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.07)', borderRadius: '10px', padding: '14px' }}>
          <div style={{ fontSize: '11px', color: '#94A3B8', marginBottom: '10px', fontFamily: "'DM Mono', monospace", letterSpacing: '1px', textTransform: 'uppercase' }}>
            Password requirements
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {RULES.map((rule) => (
              <div key={rule.label} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontFamily: "'Plus Jakarta Sans', sans-serif", color: rule.test(password) ? '#10B981' : '#5A6475' }}>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', width: '12px' }}>
                  {rule.test(password) ? '+' : '-'}
                </span>
                {rule.label}
              </div>
            ))}
          </div>
        </div>
      )}

      <Field label="Confirm Password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Re-enter password" autoComplete="new-password" fieldError={confirm && !passwordsMatch ? 'Passwords do not match' : null} required />

      <button type="submit" disabled={loading || !allPassed || !passwordsMatch} style={{
        width: '100%', padding: '13px', borderRadius: '10px', border: 'none',
        cursor: (loading || !allPassed || !passwordsMatch) ? 'not-allowed' : 'pointer',
        background: (loading || !allPassed || !passwordsMatch) ? 'rgba(99,102,241,.3)' : 'linear-gradient(135deg, #6366F1, #818CF8)',
        color: '#fff', fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: '16px',
        boxShadow: '0 4px 20px rgba(99,102,241,.25)', transition: 'opacity .2s',
        opacity: (loading || !allPassed || !passwordsMatch) ? 0.5 : 1,
      }}>
        {loading ? 'Creating account...' : 'Create Account'}
      </button>

      <div style={{ textAlign: 'center' }}>
        <button type="button" onClick={onSwitchToLogin}
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontFamily: "'Outfit', sans-serif", fontSize: '14px', color: '#818CF8', transition: 'color .15s' }}
          onMouseEnter={(e) => { e.target.style.color = '#A5B4FC' }}
          onMouseLeave={(e) => { e.target.style.color = '#818CF8' }}
        >
          Already have an account? <strong>Sign in</strong>
        </button>
      </div>
    </form>
  )
}
