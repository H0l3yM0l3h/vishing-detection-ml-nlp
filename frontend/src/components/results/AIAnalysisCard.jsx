export default function AIAnalysisCard({ explanation, scamType }) {
  if (!explanation) return null
  return (
    <div className="rounded-xl p-[1px]"
      style={{ background: 'linear-gradient(135deg, rgba(0,170,255,.3), rgba(138,43,226,.3), rgba(232,32,60,.2))' }}>
      <div className="sg-card !rounded-xl">
        <div className="sec-label mb-3">AI Intelligence Analysis</div>
        {scamType && (
          <div className="inline-block font-mono text-[10px] tracking-[2px] text-[var(--amber)] border border-[rgba(240,168,0,.25)]
            rounded px-2.5 py-1 mb-3 uppercase"
            style={{ background: 'rgba(240,168,0,.06)' }}>
            {scamType}
          </div>
        )}
        <p className="text-sm text-[var(--text)] leading-7">{explanation}</p>
      </div>
    </div>
  )
}
