export default function Footer() {
  const tags = ['TF-IDF', 'SVM v3', 'Neural Net', 'Whisper', 'ChromaDB', 'Llama 3.3 70B', 'Groq', 'RAG']
  return (
    <footer style={{
      borderTop: '1px solid rgba(255,255,255,.06)',
      padding: '28px 24px', marginTop: '32px',
      background: 'rgba(2,3,5,.7)',
      backdropFilter: 'blur(12px)',
    }}>
      <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
          {tags.map((tag) => (
            <span key={tag} style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#5A6475',
              border: '1px solid rgba(255,255,255,.07)', borderRadius: '6px',
              padding: '3px 10px', background: 'rgba(255,255,255,.03)',
            }}>{tag}</span>
          ))}
        </div>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#2E3440', letterSpacing: '0.5px' }}>
          ShieldGuard v3.1 · Hybrid Intelligence System
        </div>
      </div>
    </footer>
  )
}
