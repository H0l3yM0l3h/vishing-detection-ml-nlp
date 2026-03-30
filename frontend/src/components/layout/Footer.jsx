export default function Footer() {
  return (
    <footer className="border-t border-[var(--border)] py-6 mt-12">
      <div className="max-w-[900px] mx-auto px-6 flex flex-col items-center gap-3">
        <div className="flex items-center gap-3 flex-wrap justify-center">
          {['TF-IDF', 'SVM', 'LR', 'RF', 'NN', 'Whisper', 'ChromaDB', 'CrewAI', 'Ollama'].map((tag) => (
            <span key={tag}
              className="font-mono text-[8px] tracking-[2px] text-[var(--muted)] border border-[var(--border)] rounded px-2 py-0.5 uppercase">
              {tag}
            </span>
          ))}
        </div>
        <div className="font-mono text-[8px] text-[var(--muted)] tracking-[3px]">
          SHIELDGUARD v2.0 — HYBRID INTELLIGENCE
        </div>
      </div>
    </footer>
  )
}
