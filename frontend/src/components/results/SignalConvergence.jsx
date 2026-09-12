/**
 * Signal convergence strip.
 *
 * ShieldGuard's central claim is that it is a *hybrid* detector: a classifier,
 * a rule layer, a retrieval layer, an LLM reviewer and a threat-intelligence
 * lookup, reconciled ML-first. Until now that architecture was only visible by
 * reading six separate result cards and inferring it.
 *
 * This makes it legible at a glance: which layers ran, which found something,
 * and whether they agreed. Agreement across independent layers is the actual
 * argument for the verdict — one model saying "vishing" is an opinion, five
 * independent signals converging is evidence.
 *
 * Uses only existing tokens and the established mono/label treatment.
 */

const STATE = {
  flagged: { dot: '#EF4444', label: 'flagged' },
  clear:   { dot: '#10B981', label: 'clear' },
  idle:    { dot: '#5A6475', label: 'not run' },
}

export default function SignalConvergence({ result }) {
  if (!result) return null

  const phrases = result.suspicious_phrases?.length || 0
  const cases = result.similar_cases?.length || 0
  const intel = result.extracted_intel || {}
  const intelHits = intel.matches?.length || 0
  const identifiers =
    (intel.phones?.length || 0) + (intel.accounts?.length || 0) + (intel.urls?.length || 0)
  const aiRan = result.source === 'hybrid' && result.ai_status !== 'unavailable'
  const aiFlagged = /vishing|hang up|scam|fraud/i.test(result.ai_verdict || '')
  const mlFlagged = result.ml_label === 'vishing'
  const injection = result.prompt_injection?.detected

  const signals = [
    {
      key: 'ml',
      name: 'ML classifier',
      state: mlFlagged ? 'flagged' : 'clear',
      detail: `${Math.round((result.vishing_probability ?? 0) * 100)}% vishing probability`,
    },
    {
      key: 'rules',
      name: 'Pattern rules',
      state: phrases > 0 ? 'flagged' : 'clear',
      detail: phrases > 0 ? `${phrases} suspicious phrase${phrases === 1 ? '' : 's'}` : 'no matches',
    },
    {
      key: 'rag',
      name: 'Known scam corpus',
      state: cases > 0 ? 'flagged' : 'clear',
      detail: cases > 0 ? `${cases} similar case${cases === 1 ? '' : 's'}` : 'no close match',
    },
    {
      key: 'ai',
      name: 'AI reviewer',
      state: !aiRan ? 'idle' : aiFlagged ? 'flagged' : 'clear',
      detail: !aiRan ? 'skipped' : result.ai_verdict || 'reviewed',
    },
    {
      key: 'intel',
      name: 'Threat database',
      state: intelHits > 0 ? 'flagged' : identifiers > 0 ? 'clear' : 'idle',
      detail:
        intelHits > 0
          ? `${intelHits} known scam identifier${intelHits === 1 ? '' : 's'}`
          : identifiers > 0
            ? `${identifiers} checked, none reported`
            : 'no identifiers in call',
    },
  ]

  if (injection) {
    signals.push({
      key: 'injection',
      name: 'Manipulation check',
      state: 'flagged',
      detail: `${result.prompt_injection.count} attempt${result.prompt_injection.count === 1 ? '' : 's'} to steer the AI`,
    })
  }

  const flagged = signals.filter((s) => s.state === 'flagged').length
  const active = signals.filter((s) => s.state !== 'idle').length

  return (
    <div className="sg-card" style={{ padding: '16px 18px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
          marginBottom: 14,
        }}
      >
        <span className="sec-label" style={{ flex: '1 1 auto' }}>
          Signal convergence
        </span>
        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: flagged > 0 ? '#EF4444' : 'var(--text-3)',
            whiteSpace: 'nowrap',
          }}
        >
          {flagged} of {active} independent checks flagged
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {signals.map((s) => {
          const tone = STATE[s.state]
          return (
            <div
              key={s.key}
              style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}
            >
              <span
                aria-hidden="true"
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  flexShrink: 0,
                  background: tone.dot,
                  boxShadow: s.state === 'flagged' ? `0 0 6px ${tone.dot}` : 'none',
                }}
              />
              <span
                style={{
                  fontSize: 12.5,
                  color: 'var(--text)',
                  minWidth: 150,
                  flex: '0 0 auto',
                }}
              >
                {s.name}
              </span>
              {/* Hairline leader, echoing the .sec-label rule already used
                  throughout, so the row reads as one unit rather than two
                  floating pieces of text. */}
              <span
                aria-hidden="true"
                style={{
                  flex: '1 1 20px',
                  height: 1,
                  background: 'linear-gradient(90deg, var(--border), transparent)',
                }}
              />
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10.5,
                  color: s.state === 'flagged' ? '#EF4444' : 'var(--text-3)',
                  textAlign: 'right',
                }}
              >
                {s.detail}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
