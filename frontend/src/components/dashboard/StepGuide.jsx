const STEPS = [
  { num: '01', title: 'Capture', desc: 'Record audio, upload a file, or paste a transcript' },
  { num: '02', title: 'Analyze', desc: 'ML models + AI agents process the content' },
  { num: '03', title: 'Protect', desc: 'Get a clear verdict with explainable reasoning' },
]

export default function StepGuide() {
  return (
    <div className="flex gap-3 mb-8">
      {STEPS.map((s) => (
        <div key={s.num}
          className="flex-1 sg-card !p-4 text-center transition-colors hover:border-[rgba(0,170,255,.3)]">
          <div className="font-display text-2xl font-black text-[var(--blue)] opacity-30 leading-none mb-1.5">
            {s.num}
          </div>
          <div className="font-bold text-xs text-[var(--text)] tracking-wider uppercase">{s.title}</div>
          <div className="text-[11px] text-[var(--muted)] mt-1 leading-snug">{s.desc}</div>
        </div>
      ))}
    </div>
  )
}
