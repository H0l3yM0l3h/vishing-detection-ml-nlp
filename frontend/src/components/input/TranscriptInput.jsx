import { useState, useEffect } from 'react'
import api from '../../api/client'

export default function TranscriptInput({ onTranscriptReady }) {
  const [text, setText] = useState('')
  const [samples, setSamples] = useState(null)

  useEffect(() => {
    api.get('/samples').then((r) => setSamples(r.data)).catch(() => {})
  }, [])

  const handleAnalyze = () => {
    if (text.trim().length > 0) {
      onTranscriptReady(text.trim(), 'text')
    }
  }

  return (
    <div className="space-y-4">
      <div className="sec-label">Paste Transcript</div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={8}
        className="w-full bg-[#030a12] border border-[var(--border)] rounded-lg px-4 py-3 text-[var(--text)]
          font-mono text-sm leading-7 outline-none resize-y transition-all
          focus:border-[rgba(0,170,255,.5)] focus:shadow-[0_0_18px_rgba(0,170,255,.08)]
          placeholder:text-[#1a3355]"
        placeholder="Paste the call transcript here..."
      />

      {/* Sample buttons */}
      <div className="flex gap-3">
        {samples && (
          <>
            <button
              onClick={() => setText(samples.vishing)}
              className="flex-1 font-mono text-[9px] tracking-[2px] text-[var(--red)] border border-[rgba(232,32,60,.25)]
                rounded px-3 py-2 bg-transparent cursor-pointer hover:bg-[rgba(232,32,60,.06)] transition-colors uppercase"
            >
              Sample Vishing
            </button>
            <button
              onClick={() => setText(samples.safe)}
              className="flex-1 font-mono text-[9px] tracking-[2px] text-[var(--green)] border border-[rgba(0,232,122,.25)]
                rounded px-3 py-2 bg-transparent cursor-pointer hover:bg-[rgba(0,232,122,.06)] transition-colors uppercase"
            >
              Sample Safe
            </button>
          </>
        )}
      </div>

      <button
        onClick={handleAnalyze}
        disabled={!text.trim()}
        className="w-full font-display text-[11px] font-bold tracking-[3px] uppercase text-white
          py-3.5 rounded-lg transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed border-none"
        style={{
          background: 'linear-gradient(135deg, #b81530, #801020)',
          boxShadow: '0 4px 16px rgba(232,32,60,.28)',
        }}
      >
        ANALYZE TRANSCRIPT
      </button>
    </div>
  )
}
