import { useState } from 'react'
import api from '../../api/client'

const VERDICT_COLOR = {
  vishing:      '#e8203c',
  safe:         '#00e87a',
  inconclusive: '#f0a800',
}
const VERDICT_BG = {
  vishing:      'rgba(232,32,60,.10)',
  safe:         'rgba(0,232,122,.10)',
  inconclusive: 'rgba(240,168,0,.10)',
}

function Badge({ label, color, bg }) {
  return (
    <span className="diag-badge" style={{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: '99px',
      fontSize: '11px',
      fontFamily: "'JetBrains Mono', monospace",
      fontWeight: 700,
      letterSpacing: '0.5px',
      color,
      background: bg,
      border: `1px solid ${color}30`,
      textTransform: 'uppercase',
    }}>
      {label}
    </span>
  )
}

function MetricBox({ value, label, color }) {
  return (
    <div className="diag-metric-box" style={{
      flex: 1,
      background: 'var(--surface-2)',
      border: `1px solid ${color}30`,
      borderRadius: '12px',
      padding: '18px 14px',
      textAlign: 'center',
    }}>
      <div className="diag-metric-value" style={{
        fontFamily: "'Plus Jakarta Sans', sans-serif",
        fontWeight: 800, fontSize: '26px', color,
        marginBottom: '4px',
      }}>{value}</div>
      <div className="diag-metric-label" style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '9px', color: 'var(--text-3)',
        letterSpacing: '1.5px', textTransform: 'uppercase',
      }}>{label}</div>
    </div>
  )
}

export default function SystemDiagnostics() {
  const [open,    setOpen]    = useState(false)
  const [running, setRunning] = useState(false)
  const [data,    setData]    = useState(null)
  const [error,   setError]   = useState(null)

  const runBenchmark = async () => {
    setRunning(true)
    setError(null)
    setData(null)
    try {
      const res = await api.get('/benchmark')
      setData(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Benchmark failed - is the backend running?')
    } finally {
      setRunning(false)
    }
  }

  const toggle = () => {
    if (!open && !data) runBenchmark()
    setOpen(o => !o)
  }

  const accColor = data
    ? (data.accuracy >= 90 ? '#00e87a' : data.accuracy >= 80 ? '#f0a800' : '#e8203c')
    : 'var(--text-3)'
  const latColor = data
    ? (data.avg_latency_ms < 50 ? '#00e87a' : data.avg_latency_ms < 200 ? '#f0a800' : '#e8203c')
    : 'var(--text-3)'

  return (
    <div id="system-diagnostics" className="sg-card diag-card" style={{ marginTop: '24px', overflow: 'hidden' }}>
      {/* Header row - always visible */}
      <button
        className="diag-header"
        onClick={toggle}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'none', border: 'none', cursor: 'pointer', padding: '18px 20px',
          color: 'inherit',
        }}
      >
        <div className="diag-title-row" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px', letterSpacing: '2px', color: '#00aaff', textTransform: 'uppercase',
          }}>
            System Diagnostics
          </span>
          {data && (
            <Badge
              label={data.ready ? 'Ready for Testing' : 'Needs Review'}
              color={data.ready ? '#00e87a' : '#f0a800'}
              bg={data.ready ? 'rgba(0,232,122,.12)' : 'rgba(240,168,0,.12)'}
            />
          )}
        </div>
        <span className="diag-toggle-label" style={{ color: 'var(--text-3)', fontSize: '18px', lineHeight: 1 }}>
          {open ? 'Hide' : 'Show'}
        </span>
      </button>

      {/* Collapsible body */}
      {open && (
        <div className="diag-body" style={{ padding: '0 20px 20px', borderTop: '1px solid var(--border)' }}>

          {/* Run / Rerun button */}
          <div className="diag-run-row" style={{ paddingTop: '16px', marginBottom: '20px' }}>
            <button
              id="run-benchmark-btn"
              onClick={runBenchmark}
              disabled={running}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '8px',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px', fontWeight: 700, letterSpacing: '2px',
                textTransform: 'uppercase', color: '#fff',
                background: running ? 'rgba(99,102,241,.3)' : 'linear-gradient(135deg, #4f52c8, #6366f1)',
                border: 'none', borderRadius: '8px',
                padding: '10px 20px', cursor: running ? 'not-allowed' : 'pointer',
                opacity: running ? 0.7 : 1,
                transition: 'opacity .2s',
              }}
            >
              {running && (
                <span style={{
                  display: 'inline-block', width: '12px', height: '12px',
                  border: '2px solid rgba(255,255,255,.3)', borderTopColor: '#fff',
                  borderRadius: '50%', animation: 'spin 0.7s linear infinite',
                }} />
              )}
              {running ? 'Running...' : data ? 'Re-run Benchmark' : 'Run Benchmark'}
            </button>
            <span className="diag-run-meta" style={{
              marginLeft: '12px',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '9px', color: 'var(--text-3)',
            }}>
              10 labelled samples | SVM v3 | ML-only (no Groq required)
            </span>
          </div>

          {error && (
            <div style={{
              background: 'rgba(232,32,60,.1)', border: '1px solid rgba(232,32,60,.3)',
              borderRadius: '8px', padding: '12px 16px', marginBottom: '16px',
              fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: '#e8203c',
            }}>
              {error}
            </div>
          )}

          {data && (
            <>
              {/* Metric row */}
              <div className="diag-metric-grid" style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
                <MetricBox value={`${data.accuracy}%`}         label="ML Accuracy"    color={accColor} />
                <MetricBox value={`${data.avg_latency_ms}ms`} label="Avg Latency"    color={latColor} />
                <MetricBox value={`${data.max_latency_ms}ms`} label="Max Latency"    color={latColor} />
                <MetricBox value={`${data.correct}/${data.total}`} label="Correct"   color={accColor} />
              </div>

              {/* Threshold info */}
              <div className="diag-threshold-row" style={{
                display: 'flex', gap: '8px', marginBottom: '18px', flexWrap: 'wrap',
              }}>
                {[
                  { label: `Vishing Threshold: ${data.vishing_threshold * 100}%`,  color: '#e8203c' },
                  { label: `Reject Threshold: ${data.reject_threshold * 100}%`,    color: '#f0a800' },
                  { label: 'Provost & Fawcett, 2001',                               color: '#00aaff' },
                  { label: "Chow's Reject Option, 1970",                            color: '#00aaff' },
                ].map(b => (
                  <Badge key={b.label} label={b.label} color={b.color} bg={`${b.color}15`} />
                ))}
              </div>

              {/* Per-sample table */}
              <div style={{
                background: 'var(--surface-2)', borderRadius: '10px',
                border: '1px solid var(--border)', overflowX: 'auto', WebkitOverflowScrolling: 'touch',
              }}>
                {/* Table header */}
                <div className="diag-table-grid" style={{
                  display: 'grid',
                  gridTemplateColumns: '32px 90px 90px 90px 72px 72px minmax(150px, 1fr)',
                  padding: '8px 14px',
                  borderBottom: '1px solid var(--border)',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '9px', color: 'var(--text-3)',
                  letterSpacing: '1px', textTransform: 'uppercase',
                }}>
                  <span>#</span>
                  <span>Expected</span>
                  <span>Got</span>
                  <span>Result</span>
                  <span>Conf</span>
                  <span>Latency</span>
                  <span>Transcript Preview</span>
                </div>

                {/* Rows */}
                {data.cases.map((c) => {
                  const vc = VERDICT_COLOR[c.got] || '#8892a4'
                  const vb = VERDICT_BG[c.got]   || 'transparent'
                  return (
                    <div
                      className="diag-table-grid"
                      key={c.index}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '32px 90px 90px 90px 72px 72px minmax(150px, 1fr)',
                        padding: '9px 14px',
                        borderBottom: '1px solid var(--border)',
                        alignItems: 'center',
                        background: c.pass ? 'transparent' : 'rgba(232,32,60,.04)',
                      }}
                    >
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: '11px', color: 'var(--text-3)',
                      }}>
                        {c.index < 10 ? `0${c.index}` : c.index}
                      </span>
                      <span>
                        <Badge
                          label={c.expected}
                          color={VERDICT_COLOR[c.expected] || '#8892a4'}
                          bg={VERDICT_BG[c.expected] || 'transparent'}
                        />
                      </span>
                      <span>
                        <Badge label={c.got} color={vc} bg={vb} />
                      </span>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: '12px',
                        color: c.pass ? '#00e87a' : '#e8203c',
                        fontWeight: 700,
                      }}>
                        {c.pass ? 'PASS' : 'FAIL'}
                      </span>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: '11px', color: 'var(--text)',
                      }}>
                        {Math.round(c.confidence * 100)}%
                      </span>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: '11px',
                        color: c.latency_ms < 50 ? '#00e87a' : '#f0a800',
                      }}>
                        {c.latency_ms}ms
                      </span>
                      <span style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: '10px', color: 'var(--text-3)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {c.transcript_preview}
                      </span>
                    </div>
                  )
                })}
              </div>

              {/* Status footer */}
              <div style={{
                marginTop: '14px',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px',
                color: data.ready ? '#00e87a' : '#f0a800',
                textAlign: 'center',
              }}>
                {data.ready
                  ? 'Ready: system is performing within expected parameters for user testing.'
                  : '! Some cases were inconclusive. Check Groq API connection for full hybrid analysis.'}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
