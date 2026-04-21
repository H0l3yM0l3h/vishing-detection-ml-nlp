export default function VerdictCard({ verdict, confidence, source }) {
  const isVishing    = verdict?.toLowerCase().includes('vishing') || verdict?.toLowerCase().includes('hang up')
  const isSafe       = verdict?.toLowerCase().includes('safe')    || verdict?.toLowerCase().includes('legitimate')
  const isDivergence = verdict?.includes('UNCONFIRMED')

  const color  = isVishing ? '#EF4444' : isSafe ? '#10B981' : '#F59E0B'
  const bg     = isVishing ? 'rgba(239,68,68,.08)' : isSafe ? 'rgba(16,185,129,.08)' : 'rgba(245,158,11,.08)'
  const brd    = isVishing ? 'rgba(239,68,68,.35)'  : isSafe ? 'rgba(16,185,129,.3)' : 'rgba(245,158,11,.3)'
  const label  = isVishing ? 'VISHING DETECTED' : isSafe ? 'CALL APPEARS SAFE' : isDivergence ? 'SUSPICIOUS — UNCONFIRMED' : 'INCONCLUSIVE'
  const cls    = isVishing ? 'verdict-vishing' : isSafe ? 'verdict-safe' : 'verdict-warn'

  return (
    <div className={`sg-card ${cls}`} style={{ background: bg, borderColor: brd }}>
      {/* Label — GRAY mono, not purple */}
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase',
        color: '#5A6475', marginBottom: '14px',
      }}>
        Threat Classification
      </div>

      {/* Verdict label — status color carries the meaning */}
      <div style={{
        fontFamily: "'Plus Jakarta Sans', sans-serif",
        fontWeight: 800, fontSize: '19px', color, marginBottom: '10px', lineHeight: 1.2,
      }}>
        {label}
      </div>

      {/* Confidence — WHITE value */}
      <div style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '14px', color: '#A0ADB8' }}>
        Confidence:{' '}
        <strong style={{ color: '#F8FAFC', fontSize: '16px' }}>{(confidence * 100).toFixed(1)}%</strong>
      </div>

      <div style={{
        marginTop: '10px', display: 'inline-block',
        background: 'rgba(255,255,255,.05)', border: '1px solid rgba(255,255,255,.1)',
        borderRadius: '6px', padding: '3px 10px',
      }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#5A6475' }}>
          {source === 'hybrid' ? 'Hybrid ML + AI' : 'ML Only'}
        </span>
      </div>
    </div>
  )
}
