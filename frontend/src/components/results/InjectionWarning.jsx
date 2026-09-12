const TYPE_LABELS = {
  instruction_override: 'Instruction override',
  role_reassignment: 'Role reassignment',
  instruction_injection: 'Injected instructions',
  system_impersonation: 'System impersonation',
  role_marker_injection: 'Chat role markers',
  verdict_steering: 'Verdict steering',
  json_forgery: 'Forged result payload',
  code_fence_injection: 'Code fence injection',
  tag_injection: 'Tag injection',
  boundary_forgery: 'Fake transcript boundary',
}

/**
 * Shown when the transcript contains text aimed at the analysis system rather
 * than at the victim — i.e. an attempt to talk the AI layer out of a vishing
 * verdict.
 *
 * This is deliberately presented as evidence of fraud, not as a warning that
 * something went wrong. A genuine caller has no reason to address an automated
 * detector, so a hit here makes the call more suspicious, not less.
 */
export default function InjectionWarning({ injection }) {
  if (!injection?.detected) return null

  const types = injection.types || []
  const matches = injection.matches || []

  return (
    <div
      role="alert"
      className="sg-card"
      style={{
        padding: '16px 18px',
        border: '1px solid rgba(239,68,68,0.35)',
        background: 'rgba(239,68,68,0.06)',
      }}
    >
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          color: '#EF4444',
          marginBottom: 8,
        }}
      >
        Adversarial content detected
      </div>

      <p
        style={{
          fontSize: 13.5,
          lineHeight: 1.6,
          color: 'var(--text)',
          margin: '0 0 12px',
        }}
      >
        This transcript contains{' '}
        <strong>
          {injection.count} attempt{injection.count === 1 ? '' : 's'}
        </strong>{' '}
        to manipulate the AI analysis layer into returning a "safe" verdict. The
        attempt was blocked, and the machine-learning verdict was not affected.
      </p>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: matches.length ? 12 : 0 }}>
        {types.map((t) => (
          <span
            key={t}
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              padding: '3px 8px',
              borderRadius: 5,
              color: '#EF4444',
              border: '1px solid rgba(239,68,68,0.3)',
              background: 'rgba(239,68,68,0.08)',
            }}
          >
            {TYPE_LABELS[t] || t}
          </span>
        ))}
      </div>

      {matches.length > 0 && (
        <details>
          <summary
            style={{
              cursor: 'pointer',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              letterSpacing: '1px',
              textTransform: 'uppercase',
              color: 'var(--text-3)',
            }}
          >
            Show flagged phrases
          </summary>
          <ul style={{ margin: '10px 0 0', paddingLeft: 18 }}>
            {matches.map((m, i) => (
              <li
                key={`${m.type}-${i}`}
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  lineHeight: 1.7,
                  color: 'var(--text-2)',
                  wordBreak: 'break-word',
                }}
              >
                {/* Rendered as plain text, never as HTML — this string is
                    attacker-controlled by definition. */}
                {m.match}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
