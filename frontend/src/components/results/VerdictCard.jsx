export default function VerdictCard({ verdict, confidence, source }) {
  const isVishing = verdict?.toLowerCase().includes('vishing') || verdict?.toLowerCase().includes('hang up')
  const isSafe = verdict?.toLowerCase().includes('safe') || verdict?.toLowerCase().includes('legitimate')
  const isDivergence = verdict?.includes('UNCONFIRMED')

  const color = isVishing ? 'var(--red)' : isSafe ? 'var(--green)' : 'var(--amber)'
  const pulseClass = isVishing ? 'animate-pulse-red' : isSafe ? 'animate-pulse-green' : ''
  const label = isVishing ? 'VISHING DETECTED' : isSafe ? 'CALL APPEARS SAFE' : isDivergence ? 'SUSPICIOUS -- UNCONFIRMED' : 'INCONCLUSIVE'

  return (
    <div
      className={`sg-card text-center ${pulseClass}`}
      style={{ borderColor: color }}
    >
      <div className="font-display text-3xl font-black tracking-wider mb-2" style={{ color }}>
        {label}
      </div>
      <div className="font-mono text-sm text-[var(--muted)]">
        Confidence: <span style={{ color }} className="font-bold">{(confidence * 100).toFixed(1)}%</span>
        <span className="ml-3 text-[10px] tracking-wider uppercase">
          [{source === 'hybrid' ? 'HYBRID ML + AI' : 'ML ONLY'}]
        </span>
      </div>
    </div>
  )
}
