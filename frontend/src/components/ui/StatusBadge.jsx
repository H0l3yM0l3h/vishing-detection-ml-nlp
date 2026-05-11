export default function StatusBadge({ source }) {
  const isHybrid = source === 'hybrid'
  return (
    <span className={`inline-flex items-center gap-1.5 font-mono text-[9px] tracking-[2px] uppercase rounded px-2.5 py-1 border
      ${isHybrid
        ? 'text-[var(--blue)] border-[rgba(0,170,255,.3)]'
        : 'text-[var(--muted)] border-[var(--border)]'
      }`}
      style={{ background: isHybrid ? 'rgba(0,170,255,.10)' : 'var(--surface-2)' }}>
      <span className={`w-1.5 h-1.5 rounded-full ${isHybrid ? 'bg-[var(--blue)]' : 'bg-[var(--muted)]'}`} />
      {isHybrid ? 'HYBRID (ML + AI)' : 'ML ONLY'}
    </span>
  )
}
