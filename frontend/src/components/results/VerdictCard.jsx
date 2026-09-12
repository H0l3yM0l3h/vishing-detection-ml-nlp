/**
 * The verdict.
 *
 * This is the one thing the user opened the app to find out, and it was set at
 * 19px — smaller than the page's own hero headline, and the same visual weight
 * as every other card around it. Now that the results screen is tiered and the
 * supporting panels are deliberately quiet, this is where the emphasis belongs.
 *
 * Two changes carry it: the verdict is set large enough to be read at a
 * glance, and it is followed by a plain-language instruction. "VISHING
 * DETECTED" tells a security student what happened; "Hang up. Do not share any
 * code or transfer any money." tells the person who just took the call what to
 * do about it.
 *
 * Palette, typefaces and card treatment are unchanged.
 */

const VERDICTS = {
  vishing: {
    label: 'Vishing detected',
    action: 'Hang up. Do not share any verification code, and do not transfer money.',
    color: '#EF4444',
    bg: 'rgba(239,68,68,.08)',
    border: 'rgba(239,68,68,.35)',
    cls: 'verdict-vishing',
  },
  safe: {
    label: 'No signs of fraud',
    action: 'Nothing in this call matches a known scam pattern. Stay cautious if money or codes come up.',
    color: '#10B981',
    bg: 'rgba(16,185,129,.08)',
    border: 'rgba(16,185,129,.3)',
    cls: 'verdict-safe',
  },
  suspicious: {
    label: 'Suspicious — unconfirmed',
    action: 'The detection layers disagreed. Treat this call as untrusted until you verify it independently.',
    color: '#F59E0B',
    bg: 'rgba(245,158,11,.08)',
    border: 'rgba(245,158,11,.3)',
    cls: 'verdict-warn',
  },
  caution: {
    label: 'Exercise caution',
    action: 'Some warning signs are present. Verify the caller through a number you already trust.',
    color: '#F59E0B',
    bg: 'rgba(245,158,11,.08)',
    border: 'rgba(245,158,11,.3)',
    cls: 'verdict-warn',
  },
  inconclusive: {
    label: 'Not enough to judge',
    action: 'There is too little in this transcript for a reliable verdict. Add more of the call and scan again.',
    color: '#F59E0B',
    bg: 'rgba(245,158,11,.08)',
    border: 'rgba(245,158,11,.3)',
    cls: 'verdict-warn',
  },
}

function classify(verdict) {
  const v = (verdict || '').toLowerCase()
  if (v.includes('vishing') || v.includes('hang up')) return VERDICTS.vishing
  if (v.includes('unconfirmed')) return VERDICTS.suspicious
  if (v.includes('caution')) return VERDICTS.caution
  if (v.includes('safe') || v.includes('legitimate')) return VERDICTS.safe
  return VERDICTS.inconclusive
}

export default function VerdictCard({ verdict, confidence, source }) {
  const v = classify(verdict)

  return (
    <div
      className={`sg-card sg-verdict-card ${v.cls}`}
      style={{ background: v.bg, borderColor: v.border }}
    >
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '10px',
          letterSpacing: '1.5px',
          textTransform: 'uppercase',
          color: 'var(--text-3)',
          marginBottom: '12px',
        }}
      >
        Threat Classification
      </div>

      {/* The answer. Sized to be read before anything else on the screen. */}
      <div
        style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontWeight: 800,
          fontSize: 'clamp(24px, 4.2vw, 34px)',
          lineHeight: 1.08,
          letterSpacing: '-0.02em',
          color: v.color,
          marginBottom: '10px',
        }}
      >
        {v.label}
      </div>

      {/* What to do about it, in words a non-technical caller understands. */}
      <p
        style={{
          fontFamily: "'Plus Jakarta Sans', sans-serif",
          fontSize: '14px',
          lineHeight: 1.6,
          color: 'var(--text-2)',
          margin: '0 0 18px',
          maxWidth: '46ch',
        }}
      >
        {v.action}
      </p>

      {/* Supporting metadata, deliberately quiet. */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          flexWrap: 'wrap',
          paddingTop: '14px',
          borderTop: '1px solid var(--border)',
        }}
      >
        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px',
            letterSpacing: '1px',
            textTransform: 'uppercase',
            color: 'var(--text-3)',
          }}
        >
          Confidence
        </span>
        <span
          style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 700,
            fontSize: '17px',
            color: 'var(--text)',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {(confidence * 100).toFixed(1)}%
        </span>

        <span
          aria-hidden="true"
          style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, var(--border), transparent)' }}
        />

        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px',
            color: 'var(--text-3)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            padding: '3px 10px',
            background: 'var(--surface-2)',
          }}
        >
          {source === 'hybrid' ? 'Hybrid ML + AI' : 'ML only'}
        </span>
      </div>
    </div>
  )
}
