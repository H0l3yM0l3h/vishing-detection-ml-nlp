import { useState } from 'react'
import { useAuthStore } from '../../hooks/useAuth'

export default function LoginForm({ onSwitchToRegister }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, loading, error } = useAuthStore()
  const [lockInfo, setLockInfo] = useState(null)
  const [remainingAttempts, setRemainingAttempts] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    const res = await login(username, password)
    if (!res.success) {
      if (res.locked) {
        setLockInfo({ minutes: res.minutes_remaining })
      }
      if (res.remaining_attempts !== undefined) {
        setRemainingAttempts(res.remaining_attempts)
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="sec-label mb-4">Operator Login</div>

      {/* Lockout warning */}
      {lockInfo && (
        <div className="border border-[var(--red)] rounded-lg p-4 text-center"
          style={{ background: 'rgba(232,32,60,.06)' }}>
          <div className="font-display text-sm text-[var(--red)] tracking-wider">ACCOUNT LOCKED</div>
          <div className="font-mono text-xs text-[var(--muted)] mt-1">
            Try again in {lockInfo.minutes} minutes
          </div>
        </div>
      )}

      {/* Error */}
      {error && !lockInfo && (
        <div className="border border-[var(--red)] rounded-lg px-4 py-2.5"
          style={{ background: 'rgba(232,32,60,.06)' }}>
          <span className="text-sm text-[var(--red)]">{error}</span>
          {remainingAttempts !== null && (
            <span className="font-mono text-[10px] text-[var(--muted)] ml-2">
              ({remainingAttempts} attempts remaining)
            </span>
          )}
        </div>
      )}

      {/* Username */}
      <div>
        <label className="font-mono text-[10px] text-[var(--muted)] tracking-[2px] uppercase block mb-1.5">
          Username
        </label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full bg-[#030a12] border border-[var(--border)] rounded-lg px-4 py-3 text-[var(--text)]
            font-mono text-sm outline-none transition-all focus:border-[rgba(0,170,255,.5)]
            focus:shadow-[0_0_18px_rgba(0,170,255,.08)]"
          placeholder="Enter username"
          autoComplete="username"
          required
        />
      </div>

      {/* Password */}
      <div>
        <label className="font-mono text-[10px] text-[var(--muted)] tracking-[2px] uppercase block mb-1.5">
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full bg-[#030a12] border border-[var(--border)] rounded-lg px-4 py-3 text-[var(--text)]
            font-mono text-sm outline-none transition-all focus:border-[rgba(0,170,255,.5)]
            focus:shadow-[0_0_18px_rgba(0,170,255,.08)]"
          placeholder="Enter password"
          autoComplete="current-password"
          required
        />
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full font-display text-[11px] font-bold tracking-[3px] uppercase text-white
          py-3.5 rounded-lg transition-all cursor-pointer disabled:opacity-50 border-none"
        style={{
          background: 'linear-gradient(135deg, #b81530, #801020)',
          boxShadow: '0 4px 16px rgba(232,32,60,.28)',
        }}
      >
        {loading ? 'AUTHENTICATING...' : 'LOGIN'}
      </button>

      {/* Switch to register */}
      <div className="text-center">
        <button
          type="button"
          onClick={onSwitchToRegister}
          className="font-mono text-[10px] text-[var(--blue)] tracking-wider bg-transparent border-none cursor-pointer
            hover:text-[var(--text)] transition-colors"
        >
          CREATE NEW ACCOUNT
        </button>
      </div>
    </form>
  )
}
