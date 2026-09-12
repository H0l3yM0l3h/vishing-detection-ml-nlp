const KIND_META = {
  phones:   { label: 'Callback number', order: 1 },
  accounts: { label: 'Payment account', order: 2 },
  urls:     { label: 'Link',            order: 3 },
}

/**
 * Identifiers lifted out of the call, cross-checked against the PenipuMY
 * scam database.
 *
 * This is the one panel on the results screen that is not an opinion about
 * the wording of the call. A transcript can be phrased innocently; the
 * account the caller wants money sent to either has fraud reports against it
 * or it does not. That makes this independent, checkable evidence — and the
 * single most directly useful thing here for someone who has just been
 * called.
 */
export default function ExtractedIntelPanel({ intel }) {
  if (!intel) return null

  const groups = ['phones', 'accounts', 'urls']
    .map((kind) => ({ kind, items: intel[kind] || [] }))
    .filter((g) => g.items.length > 0)
    .sort((a, b) => KIND_META[a.kind].order - KIND_META[b.kind].order)

  if (groups.length === 0) return null

  const matchByValue = new Map((intel.matches || []).map((m) => [String(m.value), m]))
  const hasHit = matchByValue.size > 0

  return (
    <div
      className="sg-card"
      style={{
        padding: '18px 20px',
        border: hasHit ? '1px solid rgba(239,68,68,0.4)' : '1px solid var(--border)',
        background: hasHit ? 'rgba(239,68,68,0.05)' : undefined,
      }}
    >
      <div className="sec-label" style={{ marginBottom: 4 }}>
        What this caller asked you to contact
      </div>

      <p
        style={{
          fontSize: 13,
          lineHeight: 1.6,
          color: hasHit ? 'var(--text)' : 'var(--text-2)',
          margin: '0 0 16px',
        }}
      >
        {hasHit
          ? intel.summary
          : intel.checked
            ? 'These were checked against the PenipuMY scam database. None of them has been reported yet — which does not make the call safe, only unreported.'
            : 'These were found in the call. The scam database could not be reached, so they have not been checked.'}
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {groups.map(({ kind, items }) =>
          items.map((item) => {
            const hit = matchByValue.get(String(item.normalized))
            return (
              <div
                key={`${kind}-${item.normalized}`}
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'baseline',
                  gap: '6px 12px',
                  padding: '10px 12px',
                  borderRadius: 8,
                  border: hit
                    ? '1px solid rgba(239,68,68,0.35)'
                    : '1px solid var(--border)',
                  background: hit ? 'rgba(239,68,68,0.07)' : 'var(--surface-2)',
                }}
              >
                <span
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9,
                    letterSpacing: '1.5px',
                    textTransform: 'uppercase',
                    color: 'var(--text-3)',
                    minWidth: 118,
                  }}
                >
                  {KIND_META[kind].label}
                </span>

                <span
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 13,
                    color: hit ? '#EF4444' : 'var(--text)',
                    fontWeight: hit ? 700 : 500,
                    wordBreak: 'break-all',
                  }}
                >
                  {item.value}
                </span>

                {hit ? (
                  <span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      padding: '2px 8px',
                      borderRadius: 5,
                      color: '#EF4444',
                      border: '1px solid rgba(239,68,68,0.4)',
                      background: 'rgba(239,68,68,0.12)',
                    }}
                  >
                    {hit.reports > 0
                      ? `${hit.reports} fraud report${hit.reports === 1 ? '' : 's'}`
                      : 'Known scam'}
                  </span>
                ) : (
                  <span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10,
                      color: 'var(--text-3)',
                    }}
                  >
                    {intel.checked ? 'no reports on file' : 'not checked'}
                  </span>
                )}
              </div>
            )
          }),
        )}
      </div>

      {hasHit && (
        <p
          style={{
            fontSize: 13,
            lineHeight: 1.6,
            color: 'var(--text)',
            margin: '16px 0 0',
            paddingTop: 14,
            borderTop: '1px solid var(--border)',
          }}
        >
          Do not send money to this account or call this number back. If you
          already have, contact your bank immediately and report it to the
          National Scam Response Centre on <strong>997</strong>.
        </p>
      )}
    </div>
  )
}
