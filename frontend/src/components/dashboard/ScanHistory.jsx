import { useEffect, useState } from 'react'
import api from '../../api/client'

export default function ScanHistory() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/history?limit=10')
      .then((r) => setHistory(r.data.history || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return null
  if (history.length === 0) return null

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
