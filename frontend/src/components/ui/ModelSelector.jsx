const MODELS = ['SVM', 'Logistic Regression', 'Random Forest', 'Neural Network']

export default function ModelSelector({ value, onChange }) {
  return (
    <details className="sg-card !p-0 group">
      <summary className="px-4 py-3 cursor-pointer list-none flex items-center justify-between">
        <span className="sec-label !mb-0">Advanced Settings</span>
        <span className="font-mono text-[10px] text-[var(--muted)] tracking-wider group-open:rotate-180 transition-transform">
          ▼
        </span>
      </summary>
      <div className="px-4 pb-4 space-y-3">
        <label className="font-mono text-[10px] text-[var(--muted)] tracking-[2px] uppercase block">
          ML Model
        </label>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full bg-[#030a12] border border-[var(--border)] rounded-lg px-4 py-2.5
            text-[var(--text)] font-mono text-sm outline-none
            focus:border-[rgba(0,170,255,.5)] cursor-pointer appearance-none"
        >
          {MODELS.map((m) => (
            <option key={m} value={m} style={{ background: '#030a12' }}>{m}</option>
          ))}
        </select>
      </div>
    </details>
  )
}
