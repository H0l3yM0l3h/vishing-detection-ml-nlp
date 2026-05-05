import { useState, useEffect } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  BarChart, Bar,
} from 'recharts'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import Header from '../components/layout/Header'
import Footer from '../components/layout/Footer'
import NeuralBackground from '../components/ui/flow-field-background'

// ── Colour palette ────────────────────────────────────────────
const C = {
  red:    '#EF4444',
  green:  '#10B981',
  amber:  '#F59E0B',
  indigo: '#6366F1',
  blue:   '#3B82F6',
  cyan:   '#06B6D4',
  muted:  '#5A6475',
  text2:  '#A0ADB8',
  text:   '#F8FAFC',
  border: 'rgba(255,255,255,0.07)',
  surface:'rgba(8,10,18,0.72)',
}

const PIE_COLORS = { Vishing: C.red, Safe: C.green, Inconclusive: C.amber }

// ── KPI card ──────────────────────────────────────────────────
function KPICard({ label, value, sub, accent = C.indigo }) {
  return (
    <div style={{
      background: C.surface,
      backdropFilter: 'blur(16px)',
      border: `1px solid ${accent}25`,
      borderRadius: 14,
      padding: '22px 20px',
      flex: 1,
      minWidth: 160,
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase',
        color: C.muted, marginBottom: 8,
      }}>{label}</div>
      <div style={{
        fontFamily: "'Plus Jakarta Sans', sans-serif",
        fontWeight: 800, fontSize: 30, color: accent, lineHeight: 1,
      }}>{value}</div>
      {sub && (
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, color: C.muted, marginTop: 6, opacity: 0.7,
        }}>{sub}</div>
      )}
    </div>
  )
}

// ── Chart card container ──────────────────────────────────────
function ChartCard({ title, children, style }) {
  return (
    <div className="sg-card" style={{ padding: '20px 22px', ...style }}>
      <div className="sec-label" style={{ marginBottom: 18 }}>{title}</div>
      {children}
    </div>
  )
}

// ── Tooltip ───────────────────────────────────────────────────
const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'rgba(8,10,18,0.95)',
      border: '1px solid rgba(99,102,241,0.25)',
      borderRadius: 8, padding: '10px 14px',
      fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
    }}>
      {label && <div style={{ color: C.muted, marginBottom: 4 }}>{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || C.text }}>
          {p.name}: <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────
export default function AdminDashboard() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [ts, setTs]           = useState(null)
  const navigate = useNavigate()

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/analytics')
      setData(res.data)
      setTs(new Date().toLocaleTimeString())
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative' }}>

      {/* Background */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0 }}>
        <NeuralBackground color="#6366f1" trailOpacity={0.08} speed={0.4} particleCount={300} />
      </div>

      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header />

        <main style={{ flex: 1, width: '100%', display: 'flex', justifyContent: 'center' }}>
          <div style={{ maxWidth: 1100, width: '100%', padding: '0 24px 60px' }} className="animate-fade-up">

            {/* ── Title bar ── */}
            <div style={{
              display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
              margin: '32px 0 28px', flexWrap: 'wrap', gap: 16,
            }}>
              <div>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase',
                  color: C.indigo, marginBottom: 6,
                }}>
                  Command Center
                </div>
                <h1 style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontSize: 28, fontWeight: 800, color: C.text, lineHeight: 1.1, margin: 0,
                }}>
                  Analytics Dashboard
                </h1>
                {ts && (
                  <div style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9, color: C.muted, marginTop: 6,
                  }}>
                    Last refreshed at {ts}
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  id="refresh-analytics-btn"
                  onClick={loadData}
                  disabled={loading}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase',
                    color: '#fff',
                    background: loading ? 'rgba(99,102,241,0.25)' : 'linear-gradient(135deg,#4f52c8,#6366f1)',
                    border: 'none', borderRadius: 8, padding: '9px 18px',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex', alignItems: 'center', gap: 6,
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading && (
                    <span style={{
                      display: 'inline-block', width: 10, height: 10,
                      border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff',
                      borderRadius: '50%', animation: 'spin 0.7s linear infinite',
                    }} />
                  )}
                  {loading ? 'Loading' : 'Refresh'}
                </button>
                <button
                  id="back-to-app-btn"
                  onClick={() => navigate('/app')}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase',
                    color: C.text2,
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 8, padding: '9px 18px', cursor: 'pointer',
                  }}
                >
                  Back to Scanner
                </button>
              </div>
            </div>

            {/* ── Error ── */}
            {error && (
              <div style={{
                background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
                borderRadius: 10, padding: '12px 18px', marginBottom: 20,
                fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: C.red,
              }}>
                {error}
              </div>
            )}

            {/* ── Loader ── */}
            {loading && !data && (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '100px 0' }}>
                <div style={{
                  width: 36, height: 36,
                  border: '3px solid rgba(99,102,241,0.2)', borderTopColor: C.indigo,
                  borderRadius: '50%', animation: 'spin 0.8s linear infinite',
                }} />
              </div>
            )}

            {data && (
              <>
                {/* ── KPI row ── */}
                <div style={{ display: 'flex', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
                  <KPICard
                    label="Total Analyses"
                    value={data.total_scans.toLocaleString()}
                    sub="Lifetime scans recorded"
                    accent={C.indigo}
                  />
                  <KPICard
                    label="Registered Users"
                    value={data.total_users}
                    sub="Unique accounts"
                    accent={C.blue}
                  />
                  <KPICard
                    label="Vishing Rate"
                    value={`${data.vishing_rate}%`}
                    sub="Flagged as threats"
                    accent={data.vishing_rate > 50 ? C.red : C.amber}
                  />
                  <KPICard
                    label="Avg Confidence"
                    value={`${data.avg_confidence}%`}
                    sub="Mean ML confidence"
                    accent={C.green}
                  />
                </div>

                {/* ── Row 2: Pie + Area ── */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginBottom: 16 }}>

                  {/* Verdict donut */}
                  <ChartCard title="Verdict Breakdown">
                    {data.verdict_distribution.length > 0 ? (
                      <ResponsiveContainer width="100%" height={230}>
                        <PieChart>
                          <Pie
                            data={data.verdict_distribution}
                            cx="50%" cy="50%"
                            innerRadius={58} outerRadius={88}
                            paddingAngle={3}
                            dataKey="value"
                            strokeWidth={0}
                          >
                            {data.verdict_distribution.map((entry) => (
                              <Cell key={entry.name} fill={PIE_COLORS[entry.name] || C.indigo} />
                            ))}
                          </Pie>
                          <Tooltip content={<ChartTooltip />} />
                          <Legend
                            formatter={(value) => (
                              <span style={{
                                fontFamily: "'JetBrains Mono',monospace",
                                fontSize: 9, color: C.text2, letterSpacing: '0.5px',
                              }}>{value}</span>
                            )}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    ) : (
                      <div style={{
                        textAlign: 'center', color: C.muted, padding: '60px 0',
                        fontFamily: "'JetBrains Mono',monospace", fontSize: 11,
                      }}>
                        No scans recorded yet
                      </div>
                    )}
                  </ChartCard>

                  {/* Daily trend */}
                  <ChartCard title="Detection Trend  /  Last 7 Days">
                    <ResponsiveContainer width="100%" height={230}>
                      <AreaChart data={data.daily_trend} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="gVishing" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor={C.red}   stopOpacity={0.25} />
                            <stop offset="95%" stopColor={C.red}   stopOpacity={0}    />
                          </linearGradient>
                          <linearGradient id="gSafe" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor={C.green} stopOpacity={0.25} />
                            <stop offset="95%" stopColor={C.green} stopOpacity={0}    />
                          </linearGradient>
                          <linearGradient id="gTotal" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor={C.indigo} stopOpacity={0.20} />
                            <stop offset="95%" stopColor={C.indigo} stopOpacity={0}    />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="date" tick={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, fill: C.muted }} />
                        <YAxis tick={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, fill: C.muted }} allowDecimals={false} />
                        <Tooltip content={<ChartTooltip />} />
                        <Area type="monotone" dataKey="total"   name="Total"   stroke={C.indigo} fill="url(#gTotal)"   strokeWidth={2} dot={false} />
                        <Area type="monotone" dataKey="vishing" name="Vishing" stroke={C.red}    fill="url(#gVishing)" strokeWidth={2} dot={false} />
                        <Area type="monotone" dataKey="safe"    name="Safe"    stroke={C.green}  fill="url(#gSafe)"    strokeWidth={2} dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </ChartCard>
                </div>

                {/* ── Row 3: Bar + Top users ── */}
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>

                  {/* Confidence histogram */}
                  <ChartCard title="Confidence Distribution">
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={data.confidence_distribution} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="range" tick={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 8, fill: C.muted }} />
                        <YAxis tick={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, fill: C.muted }} allowDecimals={false} />
                        <Tooltip content={<ChartTooltip />} />
                        <Bar dataKey="count" name="Analyses" radius={[4, 4, 0, 0]}>
                          {data.confidence_distribution.map((entry, i) => {
                            const pct = parseInt(entry.range)
                            const color = pct >= 80 ? C.red : pct >= 50 ? C.amber : C.green
                            return <Cell key={i} fill={color} fillOpacity={0.8} />
                          })}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <div style={{
                      display: 'flex', gap: 20, marginTop: 12, justifyContent: 'center',
                      fontFamily: "'JetBrains Mono',monospace", fontSize: 9,
                    }}>
                      {[
                        { label: 'Low Risk (<50%)', color: C.green },
                        { label: 'Medium (50-80%)', color: C.amber },
                        { label: 'High Risk (>80%)', color: C.red },
                      ].map(l => (
                        <span key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 5, color: C.muted }}>
                          <span style={{ width: 8, height: 8, borderRadius: 2, background: l.color, display: 'inline-block' }} />
                          {l.label}
                        </span>
                      ))}
                    </div>
                  </ChartCard>

                  {/* Top users */}
                  <ChartCard title="Top Users by Activity">
                    {data.top_users.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                        {data.top_users.map((u, i) => {
                          const maxScans = data.top_users[0]?.scans || 1
                          const pct = (u.scans / maxScans) * 100
                          const barColors = [C.indigo, C.blue, C.cyan, '#64748B', '#475569']
                          return (
                            <div key={u.username}>
                              <div style={{
                                display: 'flex', justifyContent: 'space-between', marginBottom: 5,
                                fontFamily: "'JetBrains Mono',monospace", fontSize: 10,
                              }}>
                                <span style={{ color: C.text2 }}>
                                  <span style={{ color: C.muted, marginRight: 6 }}>#{i + 1}</span>
                                  {u.username}
                                </span>
                                <span style={{ color: C.muted }}>{u.scans}</span>
                              </div>
                              <div style={{
                                height: 4, background: 'rgba(255,255,255,0.05)',
                                borderRadius: 4, overflow: 'hidden',
                              }}>
                                <div style={{
                                  height: '100%', width: `${pct}%`,
                                  background: barColors[i] || C.indigo,
                                  borderRadius: 4,
                                  transition: 'width 0.8s ease',
                                }} />
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ) : (
                      <div style={{
                        textAlign: 'center', color: C.muted, padding: '50px 0',
                        fontFamily: "'JetBrains Mono',monospace", fontSize: 11,
                      }}>
                        No user data available
                      </div>
                    )}
                  </ChartCard>
                </div>

                {/* ── System status bar ── */}
                <div className="sg-card" style={{
                  marginTop: 20, padding: '14px 22px',
                  display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'center',
                }}>
                  <div style={{
                    fontFamily: "'JetBrains Mono',monospace",
                    fontSize: 9, color: C.muted, letterSpacing: '2px', textTransform: 'uppercase',
                  }}>
                    System Status
                  </div>
                  {[
                    { label: 'ML Engine',    detail: 'SVM v3 + Neural Net' },
                    { label: 'RAG Database', detail: '1,266 indexed cases' },
                    { label: 'Groq LLM',     detail: 'Llama 3.3 70B'      },
                    { label: 'Supabase',     detail: 'Cloud PostgreSQL'    },
                  ].map(s => (
                    <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{
                        display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
                        background: C.green, boxShadow: `0 0 6px ${C.green}`,
                      }} />
                      <span style={{
                        fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: C.muted,
                      }}>
                        {s.label} — <span style={{ color: C.text }}>{s.detail}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </main>

        <Footer />
      </div>
    </div>
  )
}
