import { useEffect, useRef, useState } from 'react'

const PHRASES = [
  'ML + RAG + LLM AGENTS',
  'HYBRID INTELLIGENCE',
  '4 AI AGENTS REASONING',
  'EXPLAINABLE VERDICTS',
  '98.5% ML ACCURACY',
]

export default function HeroSection() {
  const [phraseIdx, setPhraseIdx] = useState(0)
  const [chars, setChars] = useState([])
  const [phase, setPhase] = useState('in') // 'in' | 'out'
  const svgRef = useRef(null)

  // Text cycling
  useEffect(() => {
    const interval = setInterval(() => {
      setPhase('out')
      setTimeout(() => {
        setPhraseIdx((i) => (i + 1) % PHRASES.length)
        setPhase('in')
      }, 800)
    }, 3500)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    setChars(PHRASES[phraseIdx].split(''))
  }, [phraseIdx])

  // Mouse parallax for paths
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 })
  const heroRef = useRef(null)

  const handleMouseMove = (e) => {
    if (!heroRef.current) return
    const rect = heroRef.current.getBoundingClientRect()
    setMousePos({
      x: (e.clientX - rect.left) / rect.width,
      y: (e.clientY - rect.top) / rect.height,
    })
  }

  const shiftX = (mousePos.x - 0.5) * 30
  const shiftY = (mousePos.y - 0.5) * 15

  const PATHS = Array.from({ length: 16 }, (_, i) => {
    const offset = i * 5
    const dir = i % 2 === 0 ? 1 : -1
    return {
      d: `M${-380 - offset * dir} ${-189 + i * 8}C${-380 - offset * dir} ${-189 + i * 8} ${-312 - offset * dir} ${216 - i * 6} ${152 - offset * dir} ${343 - i * 6}C${616 - offset * dir} ${470 - i * 6} ${684 - offset * dir} ${875 - i * 6} ${684 - offset * dir} ${875 - i * 6}`,
      color: ['rgba(0,170,255,.07)', 'rgba(0,170,255,.05)', 'rgba(232,32,60,.04)', 'rgba(138,43,226,.03)'][i % 4],
      delay: i * 1.3,
    }
  })

  return (
    <div
      ref={heroRef}
      onMouseMove={handleMouseMove}
      className="relative overflow-hidden text-center py-12"
    >
      {/* SVG Background Paths */}
      <svg
        ref={svgRef}
        className="absolute top-0 left-1/2 w-[900px] h-full pointer-events-none"
        viewBox="0 0 696 316"
        fill="none"
        preserveAspectRatio="xMidYMid slice"
        style={{
          transform: `translateX(-50%) translate(${shiftX}px, ${shiftY}px)`,
          transition: 'transform 0.8s ease-out',
        }}
      >
        {PATHS.map((p, i) => (
          <path key={i} d={p.d} stroke={p.color} strokeWidth={0.4 + i * 0.03}
            strokeDasharray="1200" strokeDashoffset="1200"
            style={{
              animation: `drawPath 25s linear ${p.delay}s infinite, fadePath 8s ease-in-out ${p.delay}s infinite`,
            }}
          />
        ))}
      </svg>

      {/* Tag */}
      <div className="font-display text-[10px] text-[var(--blue)] tracking-[7px] uppercase mb-3 relative z-10"
        style={{ animation: 'subtitleGlow 4s ease-in-out infinite' }}>
        AI-Powered Voice Threat Detection
      </div>

      {/* Main heading */}
      <h1 className="font-body text-[44px] font-bold text-[var(--text)] leading-tight mb-2 relative z-10">
        Detect <em className="not-italic text-[var(--red)]">Voice Scam</em><br />Attacks Instantly
      </h1>

      {/* Vaporize text cycle */}
      <div className="h-10 flex items-center justify-center relative z-10 mb-3 overflow-hidden">
        <div className="font-display text-[13px] font-bold tracking-[5px] uppercase"
          style={{
            background: 'linear-gradient(90deg, var(--blue), var(--red), var(--blue))',
            backgroundSize: '200% 100%',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            animation: 'gradShift 4s linear infinite',
          }}>
          {chars.map((c, i) => (
            <span key={`${phraseIdx}-${i}`}
              className="inline-block"
              style={{
                animation: phase === 'out'
                  ? `vaporOut 0.5s ease ${i * 0.025}s forwards`
                  : `vaporIn 0.4s ease ${i * 0.02}s both`,
              }}>
              {c === ' ' ? '\u00A0' : c}
            </span>
          ))}
        </div>
      </div>

      {/* Description */}
      <p className="text-[var(--muted)] text-base font-light max-w-[500px] mx-auto leading-relaxed relative z-10">
        Record, upload, or paste a call transcript. Our hybrid intelligence engine
        combines ML, RAG, and multi-agent LLM reasoning for an explainable verdict.
      </p>

      {/* Extra keyframes injected as style tag */}
      <style>{`
        @keyframes drawPath { to { stroke-dashoffset: 0 } }
        @keyframes fadePath { 0%,100% { opacity: .06 } 50% { opacity: .22 } }
        @keyframes subtitleGlow { 0%,100% { text-shadow: 0 0 6px rgba(0,170,255,.1) } 50% { text-shadow: 0 0 16px rgba(0,170,255,.35) } }
        @keyframes gradShift { 0% { background-position: 0% 50% } 100% { background-position: 200% 50% } }
        @keyframes vaporOut { to { opacity: 0; transform: translateY(-20px) scale(0.5); filter: blur(4px); } }
        @keyframes vaporIn { from { opacity: 0; transform: translateY(16px) scale(0.8); filter: blur(2px); } to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); } }
      `}</style>
    </div>
  )
}
