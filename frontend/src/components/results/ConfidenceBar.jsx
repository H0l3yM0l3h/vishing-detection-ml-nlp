import { useEffect, useState } from 'react'

// Hardcoded hex values so gradient alpha-blending works correctly
// (CSS variables cannot be concatenated with hex alpha suffixes)
const COLORS = {
  red:   '#EF4444',
  amber: '#F59E0B',
  green: '#10B981',
}

export default function ConfidenceBar({ confidence, verdict }) {
  const [width, setWidth] = useState(0)
  const pct = Math.round(confidence * 100)

  // Context-aware color:
  // - Low confidence (<50%) = amber (model is uncertain)
  // - High confidence + vishing = red (confirmed threat)
  // - High confidence + safe = green (confirmed safe)
  const isVishing = verdict && /vishing|hang up|scam|suspicious/i.test(verdict)
  const color = pct < 50
    ? COLORS.amber
    : isVishing
    ? COLORS.red
    : COLORS.green

  useEffect(() => {
    const t = setTimeout(() => setWidth(pct), 100)
    return () => clearTimeout(t)
  }, [pct])

  return (
    <div className="sg-card !p-4">
      <div className="flex justify-between mb-2">
        <span className="sec-label !mb-0">Confidence Score</span>
        <span className="font-display text-lg font-bold" style={{ color }}>{pct}%</span>
      </div>
      <div style={{
        height: 10,
        borderRadius: 6,
        overflow: 'hidden',
        background: 'rgba(255,255,255,0.06)',
      }}>
        <div
          style={{
            height: '100%',
            width: `${width}%`,
            borderRadius: 6,
            background: `linear-gradient(90deg, ${color}66, ${color})`,
            boxShadow: `0 0 14px ${color}55`,
            transition: 'width 1s ease-out',
          }}
        />
      </div>
      {pct < 50 && (
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '9px', color: COLORS.amber, marginTop: '8px',
          letterSpacing: '0.5px', opacity: 0.8,
        }}>
          Low confidence — model is uncertain about this classification
        </div>
      )}
    </div>
  )
}
