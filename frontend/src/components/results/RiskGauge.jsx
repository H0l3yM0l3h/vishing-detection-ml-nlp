import { useEffect, useState } from 'react'

export default function RiskGauge({ confidence, verdict = '', vishingProbability = null }) {
  const [animatedAngle, setAnimatedAngle] = useState(0)
  const pct = Math.round(confidence * 100)
  const mlRiskPct = Math.round((vishingProbability ?? confidence) * 100)

  // Determine actual risk based on verdict + confidence
  const v = (verdict || '').toLowerCase()
  const isSafe    = v.includes('safe') || v.includes('legitimate')
  const isInconclusive = v.includes('inconclusive')

  // For safe verdicts: invert — high confidence safe = LOW risk
  // For inconclusive: always CAUTION
  // For vishing: confidence = risk
  const riskPct = vishingProbability !== null
                ? mlRiskPct
                : isSafe ? Math.max(0, 100 - pct)
                : isInconclusive ? 45
                : pct

  const targetAngle = (riskPct / 100) * 180

  const color = riskPct >= 70 ? '#EF4444' : riskPct >= 45 ? '#F59E0B' : '#10B981'
  const label = riskPct >= 70 ? 'HIGH RISK' : riskPct >= 45 ? 'CAUTION' : 'LOW RISK'

  useEffect(() => {
    let frame
    const start = performance.now()
    const animate = (now) => {
      const progress = Math.min((now - start) / 1100, 1)
      const eased    = 1 - Math.pow(1 - progress, 4)
      setAnimatedAngle(eased * targetAngle)
      if (progress < 1) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [targetAngle])

  const cx = 120, cy = 108, r = 82
  const circumference = Math.PI * r
  const arcPath       = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`
  const needleAngle   = -180 + animatedAngle

  return (
    <div className="sg-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '20px 24px' }}>
      {/* Section label — gray */}
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase',
        color: '#5A6475', marginBottom: '10px', alignSelf: 'flex-start',
      }}>
        Risk Assessment
      </div>

      <svg width="240" height="132" viewBox="0 0 240 132">
        {/* Zones */}
        {[
          { s: 0, e: 0.44, c: '#10B98120' },
          { s: 0.44, e: 0.69, c: '#F59E0B20' },
          { s: 0.69, e: 1,    c: '#EF444420' },
        ].map((z, i) => {
          const sa = Math.PI + z.s * Math.PI, ea = Math.PI + z.e * Math.PI
          const x1 = cx + r * Math.cos(sa), y1 = cy + r * Math.sin(sa)
          const x2 = cx + r * Math.cos(ea), y2 = cy + r * Math.sin(ea)
          return <path key={i} d={`M ${x1} ${y1} A ${r} ${r} 0 ${z.e - z.s > 0.5 ? 1 : 0} 1 ${x2} ${y2}`} fill="none" stroke={z.c} strokeWidth="22" strokeLinecap="butt" />
        })}

        <path d={arcPath} fill="none" stroke="rgba(255,255,255,.06)" strokeWidth="3" />
        <path d={arcPath} fill="none" stroke={color} strokeWidth="3" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={circumference - (animatedAngle / 180) * circumference}
          style={{ filter: `drop-shadow(0 0 5px ${color}80)`, transition: 'stroke .5s ease' }} />

        <g transform={`rotate(${needleAngle}, ${cx}, ${cy})`}>
          <line x1={cx} y1={cy} x2={cx + r - 14} y2={cy} stroke={color} strokeWidth="2.5" strokeLinecap="round" />
          <circle cx={cx} cy={cy} r="6" fill={color} />
          <circle cx={cx} cy={cy} r="3" fill="rgba(8,10,18,.9)" />
        </g>

        {/* Percent — WHITE, not purple */}
        <text x={cx} y={cy - 14} textAnchor="middle" fill="#F8FAFC"
          fontSize="26" fontFamily="'Plus Jakarta Sans', sans-serif" fontWeight="800">
          {riskPct}%
        </text>
      </svg>

      {/* Label — status color only for this functional element */}
      <div style={{
        fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700,
        fontSize: '12px', letterSpacing: '2px', textTransform: 'uppercase',
        color, marginTop: '4px', transition: 'color .5s ease',
      }}>
        {label}
      </div>
    </div>
  )
}
