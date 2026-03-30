export default function HighlightedTranscript({ html }) {
  if (!html) return null
  return (
    <div className="sg-card !p-4">
      <div className="sec-label mb-3">Analyzed Transcript</div>
      <div
        className="font-mono text-sm text-[var(--text)] leading-7 whitespace-pre-wrap"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  )
}
