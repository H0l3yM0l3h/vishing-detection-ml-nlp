import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function ScanHistory() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get('/history?limit=10')
      .then((r) => {
        setHistory(r.data.history || [])
        setError(null)
      })
      .catch((err) => {
        // Previously `.catch(() => {})`: a failed fetch and an empty history
        // were indistinguishable — the card simply vanished, so the user could
        // not tell whether they had no scans or the request had failed.
        setError(
          err.response?.status === 503
            ? 'History is unavailable while the database is unreachable.'
            : 'Could not load your recent scans.',
        )
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="sg-card !p-4 mt-8" aria-busy="true">
        <div className="sec-label mb-3">Recent Scan History</div>
        <div className="space-y-2" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                height: 28,
                borderRadius: 6,
                background: 'var(--surface-2)',
                opacity: 0.5 - i * 0.12,
              }}
            />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="sg-card !p-4 mt-8" role="alert">
        <div className="sec-label mb-3">Recent Scan History</div>
        <p className="text-[13px]" style={{ color: 'var(--text-2)', margin: 0 }}>
          {error}
        </p>
      </div>
    )
  }

  // An empty state, rather than rendering nothing: a new user should learn
  // that this panel exists and what will appear in it.
  if (history.length === 0) {
    return (
      <div className="sg-card !p-4 mt-8">
        <div className="sec-label mb-3">Recent Scan History</div>
        <p className="text-[13px]" style={{ color: 'var(--text-3)', margin: 0 }}>
          Your scans will appear here. Analyse a call above to get started.
        </p>
      </div>
    )
  }

  return (
    <div className="sg-card !p-4 mt-8 scan-history-card">
      <div className="sec-label mb-3">Recent Scan History</div>
      <div className="scan-history-scroll overflow-x-auto">
        <table className="scan-history-table w-full text-left">
          <thead>
            <tr className="font-mono text-[9px] text-[var(--muted)] tracking-[2px] uppercase">
              <th className="py-2 pr-4">Verdict</th>
              <th className="py-2 pr-4">Confidence</th>
              <th className="py-2 pr-4">Model</th>
              <th className="py-2 pr-4">Mode</th>
              <th className="py-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {history.map((row, i) => {
              const isV = row.verdict?.toLowerCase().includes('vishing')
              const color = isV ? 'var(--red)' : 'var(--green)'
              return (
                <tr key={i} className="border-t border-[var(--border)]">
                  <td data-label="Verdict" className="py-2 pr-4 font-mono text-[11px] font-bold" style={{ color }}>
                    {row.verdict}
                  </td>
                  <td data-label="Confidence" className="py-2 pr-4 font-mono text-[11px] text-[var(--text)]">
                    {(row.confidence * 100).toFixed(1)}%
                  </td>
                  <td data-label="Model" className="py-2 pr-4 font-mono text-[10px] text-[var(--muted)]">{row.model_used}</td>
                  <td data-label="Mode" className="py-2 pr-4 font-mono text-[10px] text-[var(--muted)]">{row.input_mode}</td>
                  <td data-label="Time" className="py-2 font-mono text-[10px] text-[var(--muted)]">
                    {new Date(row.analyzed_at).toLocaleString()}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
