import { useEffect, useState } from 'react'

const PHRASES = [
  'ML + RAG + Multi-Agent LLM',
  'Hybrid Intelligence Engine',
  '99.4% SVM Classifier Accuracy',
  'Fully Explainable AI Verdicts',
  '2 AI Reviewers (Groq 70B)',
]

export default function HeroSection() {
  const [phraseIdx, setPhraseIdx] = useState(0)
  const [displayed, setDisplayed] = useState('')
  const [typing,    setTyping]    = useState(true)

  useEffect(() => {
    const target = PHRASES[phraseIdx]
    let i = 0
    setDisplayed('')
    setTyping(true)
    const typeInterval = setInterval(() => {
      i++
      setDisplayed(target.slice(0, i))
      if (i >= target.length) {
        clearInterval(typeInterval)
        setTyping(false)
        setTimeout(() => {
          let j = target.length
          const eraseInterval = setInterval(() => {
            j--
            setDisplayed(target.slice(0, j))
            if (j <= 0) { clearInterval(eraseInterval); setPhraseIdx((x) => (x + 1) % PHRASES.length) }
          }, 18)
        }, 2200)
      }
    }, 38)
    return () => clearInterval(typeInterval)
  }, [phraseIdx])

  return (
    <div className="sg-hero" style={{ textAlign: 'center', padding: '56px 0 36px' }}>

      {/* Subtle pill badge */}
      <div className="sg-hero-pill" style={{
        display: 'inline-flex', alignItems: 'center', gap: '7px',
        background: 'var(--hero-pill-bg)',
        border: '1px solid var(--hero-pill-border)',
        borderRadius: '20px', padding: '5px 16px 5px 10px', marginBottom: '26px',
      }}>
        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', display: 'inline-block', boxShadow: '0 0 8px #10B981', animation: 'blink 2s ease-in-out infinite' }} />
        <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: 'var(--hero-pill-text)', fontWeight: 700 }}>
          AI-Powered Voice Threat Detection
        </span>
      </div>

      {/* Main heading — all WHITE, no purple gradient */}
      <h1 style={{
        fontFamily: "'Plus Jakarta Sans', sans-serif",
        fontWeight: 800,
        fontSize: 'clamp(34px, 5.5vw, 56px)',
        lineHeight: 1.1,
        color: 'var(--hero-text)',
        marginBottom: '12px',
        letterSpacing: '-0.5px',
      }}>
        Detect{' '}
        <span style={{ color: '#EF4444' }}>Voice Scam</span>
        {' '}Attacks<br />
        <span style={{ color: 'var(--hero-text)' }}>Instantly</span>
      </h1>

      {/* Typewriter — gray/silver, NOT purple */}
      <div className="sg-hero-typewriter" style={{ height: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '16px 0' }}>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: 'var(--hero-text-2)' }}>
          // {displayed}
          {typing && (
            <span style={{ borderLeft: '2px solid var(--hero-text-2)', marginLeft: '2px', animation: 'blink .8s step-end infinite' }}>&nbsp;</span>
          )}
        </span>
      </div>

      {/* Description */}
      <p style={{
        fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '15px',
        color: 'var(--hero-text-3)', maxWidth: '480px', margin: '0 auto', lineHeight: 1.75,
      }}>
        Record, upload, or paste a call transcript. Our hybrid intelligence engine
        combines ML classification, RAG pattern matching, and multi-agent LLM reasoning
        for a fully explainable verdict.
      </p>
    </div>
  )
}
