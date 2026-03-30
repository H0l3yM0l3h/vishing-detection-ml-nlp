export default function DivergenceWarning() {
  return (
    <div className="sg-card !p-4" style={{ borderColor: 'rgba(240,168,0,.3)', background: 'rgba(240,168,0,.03)' }}>
      <div className="flex items-center gap-3 mb-2">
        <span className="font-display text-sm font-bold text-[var(--amber)] tracking-wider">
          [!] DIVERGENCE DETECTED
        </span>
      </div>
      <p className="text-sm text-[var(--amber)] leading-relaxed opacity-80">
        The ML model and AI agents produced conflicting assessments. This call requires
        manual review. Exercise caution and do not share sensitive information until verified.
      </p>
    </div>
  )
}
