import { useEffect, useState } from 'react'

export default function ConfidenceBar({ confidence }) {
  const [width, setWidth] = useState(0)
  const pct = Math.round(confidence * 100)
  const color = pct >= 70 ? 'var(--red)' : pct >= 45 ? 'var(--amber)' : 'var(--green)'

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
      <div className="h-2.5 rounded-full overflow-hidden" style={{ background: 'var(--c2)' }}>
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{
            width: `${width}%`,
            background: `linear-gradient(90deg, ${color}88, ${color})`,
            boxShadow: `0 0 12px ${color}66`,
          }}
        />
      </div>
    </div>
  )
}
