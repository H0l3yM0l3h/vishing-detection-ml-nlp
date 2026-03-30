export default function WarnBox({ children }) {
  return (
    <div className="sg-card !p-4" style={{ borderColor: 'rgba(240,168,0,.2)', background: 'rgba(240,168,0,.03)' }}>
      <div className="flex items-start gap-3">
        <span className="font-display text-sm text-[var(--amber)] font-bold">[!]</span>
        <div className="text-sm text-[var(--amber)] opacity-80 leading-relaxed">{children}</div>
      </div>
    </div>
  )
}
