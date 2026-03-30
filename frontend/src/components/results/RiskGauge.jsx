import { useEffect, useState } from 'react'

export default function RiskGauge({ confidence }) {
  const [animatedAngle, setAnimatedAngle] = useState(0)
  const pct = Math.round(confidence * 100)
  const targetAngle = confidence * 180 // 0-180 degrees

  // Color zones
  const color = pct >= 70 ? '#e8203c' : pct >= 45 ? '#f0a800' : '#00e87a'
  const label = pct >= 70 ? 'THREAT' : pct >= 45 ? 'CAUTION' : 'SAFE'

  useEffect(() => {
    let frame
    const start = performance.now()
    const duration = 1200
    const animate = (now) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setAnimatedAngle(eased * targetAngle)
      if (progress < 1) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [targetAngle])

  // SVG parameters
  const cx = 120, cy = 110, r = 85
  const circumference = Math.PI * r // half circle

  // Arc for background
  const arcPath = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`

  // Needle rotation
  const needleAngle = -180 + animatedAngle

  // Zone arcs
  const zones = [
    { start: 0, end: 0.44, color: '#00e87a22', stroke: '#00e87a33' },
    { start: 0.44, end: 0.69, color: '#f0a80022', stroke: '#f0a80033' },
    { start: 0.69, end: 1, color: '#e8203c22', stroke: '#e8203c33' },
  ]

  return (
    <div className="sg-card flex flex-col items-center py-6">
      <div className="sec-label mb-3">Risk Assessment</div>

      <svg width="240" height="140" viewBox="0 0 240 140">
        {/* Zone arcs */}
        {zones.map((zone, i) => {
          const startAngle = Math.PI + zone.start * Math.PI
          const endAngle = Math.PI + zone.end * Math.PI
          const x1 = cx + r * Math.cos(startAngle)
          const y1 = cy + r * Math.sin(startAngle)
          const x2 = cx + r * Math.cos(endAngle)
          const y2 = cy + r * Math.sin(endAngle)
          const largeArc = zone.end - zone.start > 0.5 ? 1 : 0
          return (
            <path
              key={i}
              d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
              fill="none"
              stroke={zone.stroke}
              strokeWidth="18"
              strokeLinecap="round"
            />
          )
        })}

        {/* Track */}
        <path d={arcPath} fill="none" stroke="#112233" strokeWidth="6" strokeLinecap="round" />

        {/* Active arc */}
        <path
          d={arcPath}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (animatedAngle / 180) * circumference}
          style={{
            filter: `drop-shadow(0 0 6px ${color}66)`,
          }}
        />

        {/* Needle */}
        <g transform={`rotate(${needleAngle}, ${cx}, ${cy})`}>
          <line x1={cx} y1={cy} x2={cx + r - 15} y2={cy} stroke={color} strokeWidth="2.5" strokeLinecap="round" />
          <circle cx={cx} cy={cy} r="5" fill={color} />
          <circle cx={cx} cy={cy} r="2.5" fill="var(--bg, #04080f)" />
        </g>

        {/* Center text */}
        <text x={cx} y={cy - 15} textAnchor="middle" fill={color} fontSize="28" fontFamily="'Orbitron', sans-serif" fontWeight="900">
          {pct}%
        </text>
      </svg>

      <div className="font-display text-sm font-bold tracking-[4px] mt-1" style={{ color }}>
        {label}
      </div>
    </div>
  )
}
