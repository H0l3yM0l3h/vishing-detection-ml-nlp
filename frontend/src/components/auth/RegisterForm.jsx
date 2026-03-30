import { useState } from 'react'
import { useAuthStore } from '../../hooks/useAuth'

const RULES = [
  { label: 'At least 12 characters', test: (p) => p.length >= 12 },
  { label: 'One uppercase letter', test: (p) => /[A-Z]/.test(p) },
  { label: 'One lowercase letter', test: (p) => /[a-z]/.test(p) },
  { label: 'One number', test: (p) => /\d/.test(p) },
  { label: 'One special character', test: (p) => /[!@#$%^&*()\-_=+\[\]{}|;:,.<>?/`~"'\\]/.test(p) },
]

export default function RegisterForm({ onSwitchToLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const { register, loading, error } = useAuthStore()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password !== confirm) return
    await register(username, password)
  }

  const allPassed = RULES.every((r) => r.test(password))
  const passwordsMatch = password && confirm && password === confirm

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="sec-label mb-4">Create Account</div>

      {error && (
        <div className="border border-[var(--red)] rounded-lg px-4 py-2.5"
          style={{ background: 'rgba(232,32,60,.06)' }}>
          <span className="text-sm text-[var(--red)]">{error}</span>
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
          placeholder="3-32 chars, letters, numbers, underscores"
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
          placeholder="Create a strong password"
          autoComplete="new-password"
          required
        />
      </div>

      {/* Password hints */}
      <div className="sg-card !p-4 space-y-1.5">
        <div className="font-mono text-[9px] text-[var(--muted)] tracking-[2px] mb-2">PASSWORD REQUIREMENTS</div>
        {RULES.map((rule) => (
          <div key={rule.label} className="flex items-center gap-2 font-mono text-[10px]">
            <span className={rule.test(password) ? 'text-[var(--green)]' : 'text-[var(--muted)]'}>
              {rule.test(password) ? '[OK]' : '[  ]'}
            </span>
            <span className={rule.test(password) ? 'text-[var(--green)]' : 'text-[var(--muted)]'}>
              {rule.label}
            </span>
          </div>
        ))}
      </div>

      {/* Confirm */}
      <div>
        <label className="font-mono text-[10px] text-[var(--muted)] tracking-[2px] uppercase block mb-1.5">
          Confirm Password
        </label>
        <input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className={`w-full bg-[#030a12] border rounded-lg px-4 py-3 text-[var(--text)]
            font-mono text-sm outline-none transition-all focus:border-[rgba(0,170,255,.5)]
            focus:shadow-[0_0_18px_rgba(0,170,255,.08)]
            ${confirm && !passwordsMatch ? 'border-[var(--red)]' : 'border-[var(--border)]'}`}
          placeholder="Re-enter password"
          autoComplete="new-password"
          required
        />
        {confirm && !passwordsMatch && (
          <span className="font-mono text-[10px] text-[var(--red)] mt-1 block">Passwords do not match</span>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading || !allPassed || !passwordsMatch}
        className="w-full font-display text-[11px] font-bold tracking-[3px] uppercase text-white
          py-3.5 rounded-lg transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed border-none"
        style={{
          background: 'linear-gradient(135deg, #b81530, #801020)',
          boxShadow: '0 4px 16px rgba(232,32,60,.28)',
        }}
      >
        {loading ? 'CREATING ACCOUNT...' : 'REGISTER'}
      </button>

      <div className="text-center">
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="font-mono text-[10px] text-[var(--blue)] tracking-wider bg-transparent border-none cursor-pointer
            hover:text-[var(--text)] transition-colors"
        >
          BACK TO LOGIN
        </button>
      </div>
    </form>
  )
}
