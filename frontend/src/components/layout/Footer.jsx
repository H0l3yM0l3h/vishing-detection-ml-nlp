export default function Footer() {
  const tags = ['TF-IDF', 'SVM v3', 'Neural Net', 'Whisper', 'ChromaDB', 'Llama 3.3 70B', 'Groq', 'RAG']
  return (
    <footer style={{
      borderTop: '1px solid var(--border)',
      padding: '28px 24px', marginTop: '32px',
      background: 'var(--surface)',
      backdropFilter: 'blur(12px)',
    }}>
      <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
          {tags.map((tag) => (
            <span key={tag} style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: 'var(--text-3)',
              border: '1px solid var(--border)', borderRadius: '6px',
              padding: '3px 10px', background: 'var(--surface-2)',
            }}>{tag}</span>
          ))}
        </div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: 'var(--text-3)', letterSpacing: '0.5px' }}>
          ShieldGuard v3.1 · Hybrid Intelligence System
        </div>
      </div>
    </footer>
  )
}
