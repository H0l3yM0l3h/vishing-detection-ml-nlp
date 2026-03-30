import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../hooks/useAuth'
import LoginForm from '../components/auth/LoginForm'
import RegisterForm from '../components/auth/RegisterForm'

export default function LoginPage() {
  const [mode, setMode] = useState('login')
  const token = useAuthStore((s) => s.token)
  const navigate = useNavigate()

  useEffect(() => {
    if (token) navigate('/app', { replace: true })
  }, [token, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center px-4 animate-fade-up">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="font-display text-2xl font-black tracking-[6px] text-[var(--text)] animate-flicker">
            SHIELD<span className="text-[var(--red)]">GUARD</span>
          </div>
          <div className="font-mono text-[9px] text-[var(--blue)] tracking-[4px] uppercase mt-1">
            Vishing Detection System
          </div>
        </div>

        {/* Card */}
        <div className="sg-card sg-card-glow !p-8">
          {mode === 'login' ? (
            <LoginForm onSwitchToRegister={() => setMode('register')} />
          ) : (
            <RegisterForm onSwitchToLogin={() => setMode('login')} />
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <div className="font-mono text-[8px] text-[var(--muted)] tracking-[3px]">
            SHIELDGUARD v2.0 — HYBRID INTELLIGENCE
          </div>
        </div>
      </div>
    </div>
  )
}
