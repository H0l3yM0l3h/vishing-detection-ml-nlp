import { useState, useEffect, useId } from 'react'
import api from '../../api/client'
import { Textarea } from '../ui/textarea'
import { LiquidMetalButton } from '../ui/liquid-metal-button'
import { useTranscribeStore } from '../../hooks/useTranscribe'

export default function TranscriptInput({ onTranscriptReady }) {
  const [text, setText] = useState('')
  const [samples, setSamples] = useState(null)
  const id = useId()

  useEffect(() => {
    api.get('/samples').then((r) => setSamples(r.data)).catch(() => {})
  }, [])

  const handleAnalyze = () => {
    if (text.trim().length > 0) onTranscriptReady(text.trim(), 'text')
  }

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
            background:  'rgba(8,10,18,0.92)',
            fontFamily:  "'JetBrains Mono', monospace",
            fontSize:    '10px',
            letterSpacing: '1.5px',
            textTransform: 'uppercase',
            color:       '#5A6475',
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
            background:      'rgba(8,10,18,0.85)',
            border:          '1px solid rgba(255,255,255,.1)',
            borderRadius:    '10px',
            padding:         '16px 14px',
            color:           '#F8FAFC',
            fontFamily:      "'Plus Jakarta Sans', sans-serif",
            fontSize:        '14px',
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
            e.target.style.borderColor  = 'rgba(255,255,255,.1)'
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
            color:      '#3f3f46',
            pointerEvents: 'none',
          }}>
            {text.length} chars
          </span>
        )}
      </div>

      {/* Sample buttons */}
      {samples && (
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            type="button"
            onClick={() => setText(samples.vishing)}
            style={{
              flex: 1, fontFamily: "'JetBrains Mono', monospace",
              fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase',
              color: '#EF4444', border: '1px solid rgba(239,68,68,.25)',
              borderRadius: '6px', padding: '8px 12px', background: 'transparent',
              cursor: 'pointer', transition: 'all .2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,.07)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
          >
            Sample Vishing
          </button>
          <button
            type="button"
            onClick={() => setText(samples.safe)}
            style={{
              flex: 1, fontFamily: "'JetBrains Mono', monospace",
              fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase',
              color: '#10B981', border: '1px solid rgba(16,185,129,.25)',
              borderRadius: '6px', padding: '8px 12px', background: 'transparent',
              cursor: 'pointer', transition: 'all .2s',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(16,185,129,.07)' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
          >
            Sample Safe
          </button>
        </div>
      )}

      {/* Analyze button — Liquid Metal */}
      <LiquidMetalButton
        label="Analyze Transcript"
        onClick={handleAnalyze}
        disabled={!text.trim()}
        fullWidth
      />
    </div>
  )
}
