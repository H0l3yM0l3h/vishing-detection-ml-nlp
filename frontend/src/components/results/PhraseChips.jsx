export default function PhraseChips({ phrases }) {
  if (!phrases || phrases.length === 0) return null
  return (
    <div className="sg-card !p-4">
      <div className="sec-label mb-3">Suspicious Phrases Detected</div>
      <div className="flex flex-wrap gap-2">
        {phrases.map((p, i) => (
          <span key={i}
            className="font-mono text-[11px] text-[var(--red)] border border-[rgba(232,32,60,.3)] rounded px-2.5 py-1"
            style={{ background: 'rgba(232,32,60,.06)' }}>
            {p}
          </span>
        ))}
      </div>
    </div>
  )
}
