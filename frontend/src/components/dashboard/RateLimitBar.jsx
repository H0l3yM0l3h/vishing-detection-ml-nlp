export default function RateLimitBar({ used, max = 30 }) {
  const pct = Math.min((used / max) * 100, 100)
  const color = pct > 80 ? 'var(--red)' : pct > 50 ? 'var(--amber)' : 'var(--blue)'

  return (
    <div className="sg-card !p-3 flex items-center gap-4 mb-6">
      <span className="font-mono text-[9px] text-[var(--muted)] tracking-[2px] whitespace-nowrap uppercase">
        Scan Usage
      </span>
      <div className="flex-1 h-1.5 rounded-full" style={{ background: 'var(--c2)' }}>
        <div className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="font-mono text-[10px] tracking-wider" style={{ color }}>
        {used}/{max}
      </span>
    </div>
  )
}
