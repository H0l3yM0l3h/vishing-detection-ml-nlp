import { useState, useEffect, useId } from 'react'
import api from '../../api/client'
import { Textarea } from '../ui/textarea'
import { LiquidMetalButton } from '../ui/liquid-metal-button'
import { useAnalysisStore } from '../../hooks/useAnalysis'

export default function TranscriptInput({ onTranscriptReady }) {
  const [text, setText] = useState('')
  const [samples, setSamples] = useState(null)
  const id = useId()
  const loading = useAnalysisStore((s) => s.loading)

  useEffect(() => {
    api.get('/samples').then((r) => setSamples(r.data)).catch(() => {})
  }, [])

  const handleAnalyze = () => {
    if (text.trim().length > 0 && !loading) onTranscriptReady(text.trim(), 'text')
  }

  // Prefer the labelled library; fall back to the two legacy single strings so
  // an older backend still shows something.
  const TINT = {
    vishing: {
      text: '#EF4444',
      border: 'rgba(239,68,68,.25)',
      hover: 'rgba(239,68,68,.07)',
    },
    safe: {
      text: '#10B981',
      border: 'rgba(16,185,129,.25)',
      hover: 'rgba(16,185,129,.07)',
    },
  }

  const scenarioGroups = ['vishing', 'safe']
    .map((kind) => {
      const fromLibrary = samples?.scenarios?.[kind]
      const items =
        Array.isArray(fromLibrary) && fromLibrary.length > 0
          ? fromLibrary
          : samples?.[kind]
            ? [{ id: kind, label: `Sample ${kind}`, text: samples[kind] }]
            : []
      return { kind, tint: TINT[kind], items }
    })
    .filter((g) => g.items.length > 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

      {/* Textarea with floating/overlapping label */}
      <div style={{ position: 'relative', width: '100%' }}>
        {/* Overlapping label */}
        <label
          htmlFor={id}
          style={{
            position:    'absolute',
            top:         0,
            left:        '10px',
            transform:   'translateY(-50%)',
            zIndex:      10,
            display:     'block',
            padding:     '0 6px',
            background:  'var(--field-label-bg)',
            fontFamily:  "'JetBrains Mono', monospace",
            fontSize:    '10px',
            letterSpacing: '1.5px',
            textTransform: 'uppercase',
            color:       'var(--text-3)',
            lineHeight:  1,
            whiteSpace:  'nowrap',
            pointerEvents: 'none',
          }}
        >
          Paste Transcript
        </label>

        <Textarea
          id={id}
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder="Paste the call transcript here..."
          style={{
            width:           '100%',
            background:      'var(--field-bg)',
            border:          '1px solid var(--border)',
            borderRadius:    '10px',
            padding:         '16px 14px',
            color:           'var(--text)',
            fontFamily:      "'Plus Jakarta Sans', sans-serif",
            fontSize:        '15px',
            lineHeight:      1.7,
            resize:          'vertical',
            minHeight:       '200px',
            outline:         'none',
            transition:      'border-color .2s, box-shadow .2s',
            boxSizing:       'border-box',
          }}
          className="placeholder:text-[#2E3A4A] focus-visible:ring-0 focus-visible:outline-none"
          onFocus={(e) => {
            e.target.style.borderColor  = 'rgba(99,102,241,.45)'
            e.target.style.boxShadow    = '0 0 0 3px rgba(99,102,241,.08)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor  = 'var(--border)'
            e.target.style.boxShadow    = 'none'
          }}
        />

        {/* Character count — bottom-right corner */}
        {text.length > 0 && (
          <span style={{
            position:   'absolute',
            bottom:     '10px',
            right:      '12px',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize:   '10px',
            color:      'var(--text-3)',
            pointerEvents: 'none',
          }}>
            {text.length} chars
          </span>
        )}
      </div>

      {/* Example transcripts.
          Previously two buttons holding one example each. The library now
          covers the scam patterns that actually circulate here, plus the hard
          negatives — a genuine bank fraud call and an appointment reminder —
          which are the cases a naive keyword detector gets wrong. */}
      {scenarioGroups.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '9px', letterSpacing: '1.5px', textTransform: 'uppercase',
              color: 'var(--text-3)',
            }}
          >
            Try an example
          </span>

          {scenarioGroups.map(({ kind, tint, items }) => (
            <div
              key={kind}
              className="sg-sample-buttons"
              style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}
            >
              {items.map((s) => (
                <button
                  key={s.id}
                  className="sg-sample-button"
                  type="button"
                  title={`${kind === 'vishing' ? 'Scam' : 'Legitimate'} call example`}
                  onClick={() => setText(s.text)}
                  style={{
                    flex: '1 1 160px',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase',
                    color: tint.text, border: `1px solid ${tint.border}`,
                    borderRadius: '6px', padding: '8px 12px', background: 'transparent',
                    cursor: 'pointer', transition: 'all .2s', textAlign: 'left',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = tint.hover }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Analyze button — Liquid Metal */}
      <LiquidMetalButton
        label={loading ? 'Analyzing...' : 'Analyze Transcript'}
        onClick={handleAnalyze}
        disabled={!text.trim() || loading}
        fullWidth
      />
    </div>
  )
}
