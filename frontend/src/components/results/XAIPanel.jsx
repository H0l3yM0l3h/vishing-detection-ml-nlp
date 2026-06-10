function cleanFeatureName(feature) {
  return String(feature || '')
    .replace(/^\[(word|char)\]\s*/i, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export default function XAIPanel({ keywords }) {
  if (!keywords || keywords.length === 0) return null

  const rows = keywords
    .map(([feature, weight]) => ({
      feature: cleanFeatureName(feature),
      rawWeight: Number(weight) || 0,
      strength: Math.abs(Number(weight) || 0),
      direction: Number(weight) >= 0 ? 'vishing' : 'safe',
    }))
    .filter((row) => row.feature)

  if (rows.length === 0) return null

  const maxStrength = Math.max(...rows.map((row) => row.strength), 0.0001)

  return (
    <div className="sg-card !p-4">
      <div className="sec-label mb-3">TF-IDF Feature Analysis</div>
      <div className="font-mono text-[10px] text-[var(--muted)] mb-4 tracking-wider">
        TOP MODEL SIGNALS
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {rows.map((row, index) => {
          const pct = Math.max(5, Math.round((row.strength / maxStrength) * 100))
          const isVishing = row.direction === 'vishing'
          const color = isVishing ? '#e8203c' : '#00aaff'
          const label = isVishing ? 'Vishing signal' : 'Safe signal'

          return (
            <div key={`${row.feature}-${index}`} className="grid grid-cols-1 sm:grid-cols-[150px_1fr_96px]" style={{ gap: '12px', alignItems: 'center' }}>
              <div
                title={row.feature}
                style={{
                  fontFamily: "'Share Tech Mono', monospace",
                  fontSize: '12px',
                  color: 'var(--text-2)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {row.feature}
              </div>

              <div style={{
                height: '10px',
                borderRadius: '999px',
                background: 'var(--surface-2)',
                overflow: 'hidden',
                border: '1px solid var(--border)',
              }}>
                <div style={{
                  width: `${pct}%`,
                  height: '100%',
                  borderRadius: '999px',
                  background: color,
                  opacity: 0.82,
                  boxShadow: `0 0 16px ${color}55`,
                }} />
              </div>

              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px',
                color,
                textAlign: 'right',
                textTransform: 'uppercase',
                letterSpacing: '.6px',
              }}>
                {label}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
