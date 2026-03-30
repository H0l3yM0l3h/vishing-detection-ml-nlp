export default function InfoBox({ children }) {
  return (
    <div className="sg-card !p-4" style={{ borderColor: 'rgba(0,170,255,.2)', background: 'rgba(0,170,255,.03)' }}>
      <div className="flex items-start gap-3">
        <span className="font-display text-sm text-[var(--blue)] font-bold">[i]</span>
        <div className="text-sm text-[var(--blue)] opacity-80 leading-relaxed">{children}</div>
      </div>
    </div>
  )
}
