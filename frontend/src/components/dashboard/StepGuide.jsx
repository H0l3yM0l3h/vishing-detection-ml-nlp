const STEPS = [
  { num: '01', title: 'Capture',  desc: 'Record live audio, upload a file, or paste a transcript directly' },
  { num: '02', title: 'Analyse',  desc: 'ML classifier, RAG context search, and 2 AI reviewers reason through the content in cascade' },
  { num: '03', title: 'Assess',   desc: 'Receive an explainable verdict with evidence, tactics, and next steps' },
]

export default function StepGuide() {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '28px' }}>
      {STEPS.map((s, i) => (
        <div key={s.num}
          className="sg-card"
          style={{ position: 'relative', overflow: 'hidden', cursor: 'default', transition: 'border-color .2s, transform .2s' }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,.16)'; e.currentTarget.style.transform = 'translateY(-2px)' }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,.08)'; e.currentTarget.style.transform = 'translateY(0)' }}
        >
          {/* Ghost number — white/gray, NOT purple */}
          <div style={{
            position: 'absolute', top: '-10px', right: '10px',
            fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 800,
            fontSize: '64px', color: '#fff', opacity: 0.04, lineHeight: 1, userSelect: 'none',
          }}>
            {s.num}
          </div>

          {/* Step badge — neutral gray border */}
          <div style={{
            display: 'inline-block',
            background: 'rgba(255,255,255,.04)',
            border: '1px solid rgba(255,255,255,.1)',
            borderRadius: '6px', padding: '2px 9px', marginBottom: '12px',
          }}>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '10px', color: '#A0ADB8', letterSpacing: '1px',
            }}>
              Step {s.num}
            </span>
          </div>

          {/* Title — white */}
          <div style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 700, fontSize: '15px', color: '#F8FAFC', marginBottom: '6px',
          }}>
            {s.title}
          </div>

          {/* Desc — gray */}
          <div style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontSize: '13px', color: '#5A6475', lineHeight: 1.65,
          }}>
            {s.desc}
          </div>
        </div>
      ))}
    </div>
  )
}
