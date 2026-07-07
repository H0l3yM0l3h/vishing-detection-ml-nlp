import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../hooks/useAuth'
import api from '../api/client'
import { Eye, EyeOff } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Button } from '../components/ui/button'
import { EtheralShadow } from '../components/ui/etheral-shadow'
import TocDialog from '../components/ui/toc-dialog'

/* Password show/hide field */
function PwField({ id, label, value, onChange, placeholder = '••••••••', autoComplete }) {
  const [show, setShow] = useState(false)
  return (
    <div className="grid gap-2">
      <Label htmlFor={id} className="text-zinc-300">{label}</Label>
      <div style={{ position: 'relative' }}>
        <Input
          id={id}
          type={show ? 'text' : 'password'}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          required
          className="sg-input sg-pw-input bg-zinc-950 border-zinc-800 text-zinc-50 placeholder:text-zinc-600"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-md text-zinc-400 hover:text-zinc-200 transition-colors"
          style={{ background: 'none', border: 'none', cursor: 'pointer' }}
          aria-label={show ? 'Hide password' : 'Show password'}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  )
}

const PW_RULES = [
  { label: '12+ characters',    test: (p) => p.length >= 12 },
  { label: 'Uppercase letter',  test: (p) => /[A-Z]/.test(p) },
  { label: 'Lowercase letter',  test: (p) => /[a-z]/.test(p) },
  { label: 'Number',            test: (p) => /\d/.test(p) },
  { label: 'Special character', test: (p) => /[!@#$%^&*()\-_=+[\]{}|;:,.<>?]/.test(p) },
]

export default function LoginPage() {
  const navigate = useNavigate()
  const token    = useAuthStore((s) => s.token)
  useEffect(() => { if (token) navigate('/app', { replace: true }) }, [token, navigate])

  useEffect(() => {
    const controller = new AbortController()
    api.get('/health', { signal: controller.signal }).catch(() => {})
    return () => controller.abort()
  }, [])

  const [tab, setTab] = useState('login')
  const [showWakeupText, setShowWakeupText] = useState(false)

  // Login
  const [loginUser, setLoginUser] = useState('')
  const [loginPass, setLoginPass] = useState('')
  const [lockInfo,  setLockInfo]  = useState(null)
  const [remaining, setRemaining] = useState(null)

  // Register
  const [regUser,    setRegUser]    = useState('')
  const [regPass,    setRegPass]    = useState('')
  const [regConfirm, setRegConfirm] = useState('')
  const [tocAgreed,  setTocAgreed]  = useState(false)

  const { login, register, loading, error } = useAuthStore()

  useEffect(() => {
    if (!loading || tab !== 'login') return

    const timer = setTimeout(() => setShowWakeupText(true), 3000)
    return () => clearTimeout(timer)
  }, [loading, tab])

  const handleLogin = async (e) => {
    e.preventDefault()
    setShowWakeupText(false)
    setLockInfo(null); setRemaining(null)
    const res = await login(loginUser.trim(), loginPass)
    setShowWakeupText(false)
    if (!res?.success) {
      if (res?.locked)                            setLockInfo({ minutes: res.minutes_remaining })
      if (res?.remaining_attempts !== undefined)  setRemaining(res.remaining_attempts)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    await register(regUser.trim(), regPass)
  }

  const rulesOk  = PW_RULES.every((r) => r.test(regPass))
  const pwsMatch = regPass && regConfirm && regPass === regConfirm

  return (
    <section className="sg-login-page" style={{ position: 'fixed', inset: 0, background: 'var(--login-bg)', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>

      {/* Etheral Shadow full-viewport background */}
      <div style={{ position: 'absolute', inset: 0 }}>
        <EtheralShadow
          color="rgba(60, 55, 140, 1)"
          animation={{ scale: 85, speed: 75 }}
          noise={{ opacity: 0.5, scale: 1.2 }}
          sizing="fill"
        />
      </div>

      {/* Dark overlay to keep card legible */}
      <div style={{ position: 'absolute', inset: 0, background: 'var(--login-overlay)' }} />

      <style>{`
        .sg-login-page{--login-bg:#09090b;--login-overlay:rgba(9,9,11,0.55);--login-card:rgba(18,18,20,0.82);--login-border:#27272a;--login-input:#09090b;--login-tab:#09090b;--login-tab-active:#27272a;--login-text:#fafafa;--login-muted:#71717a;--login-muted-soft:#3f3f46;--login-rule:rgba(255,255,255,.03)}
        html[data-theme="light"] .sg-login-page{--login-bg:#F6F8FC;--login-overlay:rgba(246,248,252,0.42);--login-card:rgba(255,255,255,0.84);--login-border:rgba(15,23,42,.14);--login-input:rgba(255,255,255,.86);--login-tab:rgba(248,250,252,.78);--login-tab-active:#0f172a;--login-text:#0f172a;--login-muted:#64748b;--login-muted-soft:#94a3b8;--login-rule:rgba(15,23,42,.05)}
        .sg-input{height:40px!important;padding:0 16px!important;background:var(--login-input)!important;border-color:var(--login-border)!important;color:var(--login-text)!important}
        .sg-pw-input{padding-right:40px!important}
        .sg-input::placeholder{color:var(--login-muted-soft)!important}
        .sg-input:focus-visible{border-color:#3f3f46!important;box-shadow:0 0 0 3px rgba(99,102,241,.12)!important;outline:none!important}
        .card-animate{opacity:0;transform:translateY(16px);animation:fadeUp .65s cubic-bezier(.22,.61,.36,1) .2s forwards}
        @keyframes fadeUp{to{opacity:1;transform:translateY(0)}}
        .tab-btn{flex:1;padding:9px 0;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-family:'Plus Jakarta Sans',sans-serif;font-weight:500;transition:all .2s}
        .tab-btn.active{background:var(--login-tab-active);color:#fafafa;box-shadow:inset 0 0 0 1px rgba(99,102,241,.25)}
        .tab-btn.inactive{background:transparent;color:var(--login-muted)}
        .tab-btn.inactive:hover{color:var(--login-text)}
        html[data-theme="light"] .tab-btn.active{color:#f8fafc}
        html[data-theme="light"] .sg-login-page .text-zinc-300{color:#334155!important}
        html[data-theme="light"] .sg-login-page .text-zinc-400{color:#64748b!important}
      `}</style>

      {/* Centered card */}
      <div style={{ position: 'relative', zIndex: 1, height: '100%', display: 'grid', placeItems: 'center', padding: '0 16px' }}>
        <Card
          className="card-animate"
          style={{ width: '100%', maxWidth: '400px', border: '1px solid var(--login-border)', background: 'var(--login-card)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)' }}
        >
          {/* Header */}
          <CardHeader className="sg-login-card-header" style={{ padding: '24px 24px 4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div style={{ width: '30px', height: '30px', borderRadius: '8px', overflow: 'hidden', flexShrink: 0 }}>
                <img src="/logo.png" alt="ShieldGuard logo" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              </div>
              <CardTitle style={{ fontSize: '20px', fontWeight: 700, color: 'var(--login-text)', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                ShieldGuard
              </CardTitle>
            </div>
            <CardDescription style={{ color: 'var(--login-muted)', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
              {tab === 'login' ? 'Sign in to your account' : 'Create a new account'}
            </CardDescription>
          </CardHeader>

          <CardContent className="sg-login-card-content" style={{ padding: '4px 24px 24px' }}>
            {/* Tab switcher */}
            <div style={{ display: 'flex', gap: '4px', background: 'var(--login-tab)', border: '1px solid var(--login-border)', borderRadius: '10px', padding: '4px', marginBottom: '20px' }}>
              <button className={`tab-btn ${tab === 'login' ? 'active' : 'inactive'}`} onClick={() => setTab('login')}>
                Sign In
              </button>
              <button className={`tab-btn ${tab === 'signup' ? 'active' : 'inactive'}`} onClick={() => setTab('signup')}>
                Create Account
              </button>
            </div>

            {/* SIGN IN */}
            {tab === 'login' && (
              <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {lockInfo && (
                  <div style={{ background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.25)', borderRadius: '8px', padding: '12px', textAlign: 'center' }}>
                    <div style={{ fontWeight: 600, color: '#FCA5A5', fontSize: '14px' }}>Account locked</div>
                    <div style={{ fontSize: '12px', color: '#71717a', marginTop: '2px' }}>Try again in {lockInfo.minutes} min</div>
                  </div>
                )}
                {error && !lockInfo && (
                  <div style={{ background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.2)', borderRadius: '8px', padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '13px', color: '#FCA5A5' }}>{error}</span>
                    {remaining !== null && <span style={{ fontSize: '11px', color: '#71717a' }}>{remaining} attempts left</span>}
                  </div>
                )}
                <div className="grid gap-2">
                  <Label htmlFor="login-user" className="text-zinc-300">Username</Label>
                  <Input id="login-user" type="text" placeholder="Enter your username"
                    value={loginUser} onChange={(e) => setLoginUser(e.target.value)}
                    autoComplete="username" required
                    className="sg-input bg-zinc-950 border-zinc-800 text-zinc-50 placeholder:text-zinc-600"
                  />
                </div>
                <PwField id="login-pass" label="Password" value={loginPass}
                  onChange={(e) => setLoginPass(e.target.value)} autoComplete="current-password" />
                <Button type="submit" disabled={loading}
                  className="w-full h-10 rounded-lg bg-zinc-50 text-zinc-900 hover:bg-zinc-200 font-semibold"
                  style={{
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                    whiteSpace: showWakeupText ? 'normal' : undefined,
                    lineHeight: showWakeupText ? 1.2 : undefined,
                    fontSize: showWakeupText ? '12px' : undefined,
                    paddingInline: showWakeupText ? '10px' : undefined,
                  }}>
                  {loading ? (showWakeupText ? 'Waking up cloud backend, this may take a minute...' : 'Signing in...') : 'Sign In'}
                </Button>
              </form>
            )}

            {/* CREATE ACCOUNT */}
            {tab === 'signup' && (
              <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {error && (
                  <div style={{ background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.2)', borderRadius: '8px', padding: '10px 14px', fontSize: '13px', color: '#FCA5A5' }}>
                    {error}
                  </div>
                )}
                <div className="grid gap-2">
                  <Label htmlFor="reg-user" className="text-zinc-300">Username</Label>
                  <Input id="reg-user" type="text" placeholder="3-32 chars, letters, numbers, _"
                    value={regUser} onChange={(e) => setRegUser(e.target.value)}
                    autoComplete="username" required
                    className="sg-input bg-zinc-950 border-zinc-800 text-zinc-50 placeholder:text-zinc-600"
                  />
                </div>
                <PwField id="reg-pass" label="Password" value={regPass}
                  onChange={(e) => setRegPass(e.target.value)} autoComplete="new-password" />

                {/* PW rules compact grid */}
                {regPass.length > 0 && (
                  <div className="grid grid-cols-1 sm:grid-cols-2" style={{ gap: '4px 10px', padding: '10px 12px', background: 'var(--login-rule)', border: '1px solid var(--login-border)', borderRadius: '8px' }}>
                    {PW_RULES.map((r) => (
                      <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontFamily: "'JetBrains Mono', monospace", color: r.test(regPass) ? '#10B981' : '#3f3f46' }}>
                        <span style={{ width: '10px' }}>{r.test(regPass) ? '+' : '-'}</span>
                        {r.label}
                      </div>
                    ))}
                  </div>
                )}

                <PwField id="reg-confirm" label="Confirm Password" value={regConfirm}
                  onChange={(e) => setRegConfirm(e.target.value)}
                  placeholder="Re-enter password" autoComplete="new-password" />
                {regConfirm && !pwsMatch && (
                  <p style={{ fontSize: '12px', color: '#FCA5A5', marginTop: '-8px' }}>Passwords do not match</p>
                )}

                {/* T&C agreement row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 0' }}>
                  <div
                    onClick={() => setTocAgreed((v) => !v)}
                    style={{
                      width: '16px', height: '16px', borderRadius: '4px', flexShrink: 0, cursor: 'pointer',
                      border: `1.5px solid ${tocAgreed ? '#6366f1' : '#3f3f46'}`,
                      background: tocAgreed ? '#6366f1' : 'transparent',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all .15s',
                    }}
                  >
                    {tocAgreed && (
                      <svg width="9" height="7" viewBox="0 0 9 7" fill="none">
                        <path d="M1 3.5L3.5 6L8 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                  <span style={{ fontSize: '13px', color: 'var(--login-muted)', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    I have read and agree to the{' '}
                    <TocDialog onAgree={() => setTocAgreed(true)} />
                  </span>
                </div>

                <Button type="submit" disabled={loading || !rulesOk || !pwsMatch || !tocAgreed}
                  className="w-full h-10 rounded-lg bg-zinc-50 text-zinc-900 hover:bg-zinc-200 font-semibold disabled:opacity-40"
                  style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                  {loading ? 'Creating account...' : 'Create Account'}
                </Button>
              </form>
            )}
          </CardContent>

          <CardFooter className="sg-login-card-footer" style={{ padding: '0 24px 24px', justifyContent: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--login-muted-soft)', fontFamily: "'JetBrains Mono', monospace" }}>
              ShieldGuard v3.1 — Hybrid Intelligence System
            </span>
          </CardFooter>
        </Card>
      </div>
    </section>
  )
}
