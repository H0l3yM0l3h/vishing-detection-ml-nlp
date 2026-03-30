export default function RAGSimilarCases({ cases }) {
  if (!cases || cases.length === 0) return null
  return (
    <div className="sg-card !p-4" style={{ borderColor: 'rgba(240,168,0,.2)' }}>
      <div className="sec-label mb-3" style={{ color: 'var(--amber)' }}>Similar Historical Cases</div>
      <div className="space-y-3">
        {cases.map((c, i) => (
          <div key={i} className="rounded-lg p-3" style={{ background: 'var(--c2)', border: '1px solid var(--border)' }}>
            <div className="flex justify-between items-center mb-2">
              <span className="font-mono text-[10px] tracking-[2px] text-[var(--amber)] uppercase font-bold">
                {c.scam_type}
              </span>
              <span className="font-mono text-[10px] text-[var(--muted)]">
                {(c.similarity * 100).toFixed(0)}% match
              </span>
            </div>
            <p className="font-mono text-[11px] text-[var(--muted)] leading-5 line-clamp-3">
              {c.text_preview}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
