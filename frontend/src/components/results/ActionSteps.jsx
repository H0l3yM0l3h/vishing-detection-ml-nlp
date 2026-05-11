export default function ActionSteps({ steps }) {
  if (!steps || steps.length === 0) return null
  return (
    <div className="sg-card !p-4">
      <div className="sec-label mb-3">Recommended Actions</div>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="font-display text-sm font-bold text-[var(--blue)] opacity-50 mt-0.5">
              {String(i + 1).padStart(2, '0')}
            </span>
            <span className="text-[15px] text-[var(--text)] leading-relaxed">{step}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
