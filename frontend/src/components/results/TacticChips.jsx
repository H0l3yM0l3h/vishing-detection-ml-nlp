const TACTIC_COLORS = {
  URGENCY:     { color: 'var(--red)',   bg: 'rgba(232,32,60,.06)',  border: 'rgba(232,32,60,.3)' },
  AUTHORITY:   { color: 'var(--blue)',  bg: 'rgba(0,170,255,.06)',  border: 'rgba(0,170,255,.3)' },
  FEAR:        { color: 'var(--red)',   bg: 'rgba(232,32,60,.06)',  border: 'rgba(232,32,60,.3)' },
  ISOLATION:   { color: 'var(--amber)', bg: 'rgba(240,168,0,.06)',  border: 'rgba(240,168,0,.3)' },
  RECIPROCITY: { color: 'var(--green)', bg: 'rgba(0,232,122,.06)', border: 'rgba(0,232,122,.3)' },
}

export default function TacticChips({ tactics }) {
  if (!tactics || tactics.length === 0) return null

  return (
    <div className="sg-card !p-4">
      <div className="sec-label mb-3">Social Engineering Tactics</div>
      <div className="flex flex-wrap gap-2">
        {tactics.map((tactic, i) => {
          const key = tactic.toUpperCase().trim()
          const style = TACTIC_COLORS[key] || TACTIC_COLORS.URGENCY
          return (
            <span key={i}
              className="font-mono text-[10px] tracking-[2px] uppercase rounded px-3 py-1.5 font-bold"
              style={{ color: style.color, background: style.bg, border: `1px solid ${style.border}` }}>
              {tactic}
            </span>
          )
        })}
      </div>
    </div>
  )
}
