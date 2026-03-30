import { useAuthStore } from '../../hooks/useAuth'

export default function Header() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  return (
    <header className="relative overflow-hidden border-b border-[var(--border)]"
      style={{ background: 'linear-gradient(135deg, #040c16, #08131f 60%, #040c16)' }}>
      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-[2px]"
        style={{ background: 'linear-gradient(90deg, transparent, var(--blue), var(--red), var(--blue), transparent)' }} />

      <div className="flex w-full justify-between items-center px-6 md:px-12 py-4">
        {/* Logo */}
        <div>
          <div className="font-display text-xl font-black tracking-[5px] text-[var(--text)] animate-flicker">
            SHIELD<span className="text-[var(--red)]">GUARD</span>
          </div>
          <div className="font-mono text-[9px] text-[var(--blue)] tracking-[4px] uppercase mt-0.5">
            Vishing Detection System
          </div>
        </div>

        {/* Right section */}
        <div className="ml-auto flex items-center gap-5">
          {/* Online badge */}
          <div className="flex items-center gap-1.5 border border-[rgba(0,232,122,.22)] rounded px-3 py-1.5"
            style={{ background: 'rgba(0,232,122,.06)' }}>
            <div className="w-[5px] h-[5px] rounded-full bg-[var(--green)] animate-blink"
              style={{ boxShadow: '0 0 6px var(--green)' }} />
            <span className="font-mono text-[9px] text-[var(--green)] tracking-[2px]">SYSTEM ONLINE</span>
          </div>

          {/* User */}
          {user && (
            <span className="font-mono text-[9px] text-[var(--muted)] tracking-[2px]">
              OPERATOR: <span className="text-[var(--blue)]">{user.username.toUpperCase()}</span>
            </span>
          )}

          {/* Logout */}
          <button
            onClick={logout}
            className="font-mono text-[9px] tracking-[2px] text-[var(--muted)] border border-[var(--border)] px-3 py-1.5 rounded
              hover:border-[var(--red)] hover:text-[var(--red)] transition-colors cursor-pointer bg-transparent"
          >
            LOGOUT
          </button>
        </div>
      </div>
    </header>
  )
}
