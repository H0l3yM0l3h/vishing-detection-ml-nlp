import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/layout/Header'
import Footer from '../components/layout/Footer'
import NeuralBackground from '../components/ui/flow-field-background'
import { useThreatIntelStore } from '../hooks/useThreatIntel'

// ── Colour palette (exact same as AdminDashboard) ──────────────
const C = {
  red:    '#EF4444',
  green:  '#10B981',
  amber:  '#F59E0B',
  indigo: '#6366F1',
  blue:   '#3B82F6',
  cyan:   '#06B6D4',
  muted:  'var(--text-3)',
  text2:  'var(--text-2)',
  text:   'var(--hero-text)',
  cardText: 'var(--text)',
  border: 'var(--border)',
  surface:'var(--surface)',
}

// ── KPI card (same component as AdminDashboard) ────────────────
function KPICard({ label, value, sub, accent = C.indigo }) {
  return (
    <div className="sg-kpi-card" style={{
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

// ── Section label (identical to .sec-label CSS class) ──────────
function SecLabel({ children }) {
  return (
    <div className="sec-label" style={{ marginBottom: 18 }}>{children}</div>
  )
}

// ── Verdict pill ───────────────────────────────────────────────
function StatusPill({ label, color, glow = false }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 10, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase',
      color,
      background: `${color}14`,
      border: `1px solid ${color}35`,
      borderRadius: 8, padding: '5px 14px',
      boxShadow: glow ? `0 0 16px ${color}25` : 'none',
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: '50%', background: color,
        boxShadow: `0 0 8px ${color}`,
        display: 'inline-block',
      }} />
      {label}
    </span>
  )
}

// ── Phone result card ──────────────────────────────────────────
function PhoneResultCard({ data }) {
  const isFraud = data.fraud === true
  const isSpam = data.spam === true
  const isSafe = !isFraud && !isSpam && data.police_report_count === 0 && data.verified_report_count === 0
  const hasBusiness = data.business && data.business !== null

  const statusColor = isFraud ? C.red : isSpam ? C.amber : isSafe ? C.green : C.amber
  const statusLabel = isFraud ? 'FRAUD FLAGGED' : isSpam ? 'SPAM REPORTED' : isSafe ? 'NO REPORTS' : 'REPORTS FOUND'

  return (
    <div className="sg-card sg-intel-result-card animate-fade-up" style={{ borderColor: `${statusColor}35` }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase',
            color: C.muted, marginBottom: 6,
          }}>Phone Lookup Result</div>
          <div style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800, fontSize: 22, color: C.cardText,
          }}>{data.phone}</div>
        </div>
        <StatusPill label={statusLabel} color={statusColor} glow={isFraud} />
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <StatBox
          label="Police Reports"
          value={data.police_report_count}
          accent={data.police_report_count > 0 ? C.red : C.green}
        />
        <StatBox
          label="Verified Reports"
          value={data.verified_report_count}
          accent={data.verified_report_count > 0 ? C.amber : C.green}
        />
        <StatBox
          label="Report Status"
          value={data.police_report_status?.toUpperCase() || 'N/A'}
          accent={C.indigo}
          isText
        />
        <StatBox
          label="Fraud Flag"
          value={data.fraud ? 'YES' : 'NO'}
          accent={data.fraud ? C.red : C.green}
          isText
        />
        <StatBox
          label="Spam Flag"
          value={data.spam ? 'YES' : 'NO'}
          accent={data.spam ? C.amber : C.green}
          isText
        />
      </div>

      {/* Business info */}
      {hasBusiness && (
        <div style={{
          background: 'var(--surface-2)',
          border: '1px solid var(--border)',
          borderRadius: 12, padding: 18, marginTop: 4,
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase',
            color: C.muted, marginBottom: 14,
          }}>Verified Business</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            {data.business.logo_url && (
              <img
                src={data.business.logo_url}
                alt={data.business.brand_name}
                style={{
                  width: 44, height: 44, borderRadius: 10,
                  objectFit: 'cover', background: '#fff',
                  border: '1px solid var(--border)',
                }}
              />
            )}
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 700, fontSize: 16, color: C.cardText, marginBottom: 3,
              }}>{data.business.display_name || data.business.brand_name}</div>
              {data.business.address && (
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10, color: C.muted, marginBottom: 4,
                }}>{data.business.address}</div>
              )}
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 6 }}>
                {data.business.tier && (
                  <StatusPill
                    label={data.business.tier === 'verified_spoofing' ? 'SPOOFING ALERT' : data.business.tier.toUpperCase()}
                    color={data.business.tier === 'verified' ? C.green : data.business.tier === 'verified_spoofing' ? C.red : C.amber}
                  />
                )}
                {data.business.rating && (
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10, color: C.amber,
                  }}>★ {data.business.rating} ({data.business.review_count} reviews)</span>
                )}
                {data.business.opening_hours_status && (
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10, color: C.muted,
                  }}>{data.business.opening_hours_status}</span>
                )}
              </div>
            </div>
          </div>
          {data.business.scam_alert_banner && (
            <div style={{
              marginTop: 12, padding: '10px 14px',
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.25)',
              borderRadius: 8,
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11, color: C.red,
            }}>{data.business.scam_alert_banner}</div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Bank result card ───────────────────────────────────────────
function BankResultCard({ data }) {
  const isFraud = data.fraud === true
  const isSafe = !isFraud && data.police_report_count === 0 && data.verified_report_count === 0

  const statusColor = isFraud ? C.red : isSafe ? C.green : C.amber
  const statusLabel = isFraud ? 'FRAUD FLAGGED' : isSafe ? 'NO REPORTS' : 'REPORTS FOUND'

  return (
    <div className="sg-card sg-intel-result-card animate-fade-up" style={{ borderColor: `${statusColor}35` }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase',
            color: C.muted, marginBottom: 6,
          }}>Bank Account Lookup</div>
          <div style={{
            fontFamily: "'Plus Jakarta Sans', sans-serif",
            fontWeight: 800, fontSize: 22, color: C.cardText,
          }}>{data.bank_account}</div>
        </div>
        <StatusPill label={statusLabel} color={statusColor} glow={isFraud} />
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        {data.holder_name && (
          <StatBox label="Account Holder" value={data.holder_name} accent={C.indigo} isText />
        )}
        {data.bank_name && (
          <StatBox label="Bank" value={data.bank_name} accent={C.blue} isText />
        )}
        <StatBox
          label="Police Reports"
          value={data.police_report_count}
          accent={data.police_report_count > 0 ? C.red : C.green}
        />
        <StatBox
          label="Verified Reports"
          value={data.verified_report_count}
          accent={data.verified_report_count > 0 ? C.amber : C.green}
        />
        <StatBox
          label="Report Status"
          value={data.police_report_status?.toUpperCase() || 'N/A'}
          accent={C.indigo}
          isText
        />
        <StatBox
          label="Fraud"
          value={data.fraud ? 'YES' : 'NO'}
          accent={data.fraud ? C.red : C.green}
          isText
        />
      </div>
    </div>
  )
}

// ── Search results card ────────────────────────────────────────
function SearchResultsCard({ data }) {
  if (!data || !data.results || data.results.length === 0) {
    return (
      <div className="sg-card sg-intel-result-card animate-fade-up">
        <SecLabel>Search Results</SecLabel>
        <div style={{
          textAlign: 'center', padding: '40px 0',
          fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: C.muted,
        }}>
          No scam profiles found for "{data?.query}"
        </div>
      </div>
    )
  }

  return (
    <div className="sg-card sg-intel-result-card animate-fade-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18, flexWrap: 'wrap', gap: 8 }}>
        <SecLabel>Search Results</SecLabel>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10, color: C.muted,
        }}>{data.count} profile{data.count !== 1 ? 's' : ''} found</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {data.results.map((profile, i) => (
          <div key={profile.profile_id || i} style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border)',
            borderRadius: 12, padding: 16,
            transition: 'border-color 0.2s',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10, flexWrap: 'wrap', gap: 8 }}>
              <div>
                <div style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontWeight: 700, fontSize: 15, color: C.cardText, marginBottom: 2,
                }}>{profile.name || 'Unknown'}</div>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9, color: C.muted, letterSpacing: '0.5px',
                }}>{profile.profile_id}</div>
              </div>
              <StatusPill
                label={`${profile.total_reports} REPORTS`}
                color={profile.total_reports > 3 ? C.red : profile.total_reports > 0 ? C.amber : C.green}
              />
            </div>

            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <MiniStat label="Total Loss" value={`RM ${(profile.total_loss_myr || 0).toLocaleString()}`} color={C.red} />
              <MiniStat label="Phone Numbers" value={profile.asset_counts?.phone_numbers || 0} color={C.indigo} />
              <MiniStat label="Bank Accounts" value={profile.asset_counts?.bank_accounts || 0} color={C.blue} />
              <MiniStat label="Social Accounts" value={profile.asset_counts?.social_accounts || 0} color={C.cyan} />
              <MiniStat label="Last Updated" value={profile.last_updated?.split(' ')[0] || '—'} color={C.muted} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Reusable stat box ──────────────────────────────────────────
function StatBox({ label, value, accent = C.indigo, isText = false }) {
  return (
    <div style={{
      flex: '1 1 120px', minWidth: 100,
      background: 'var(--surface-2)',
      border: '1px solid var(--border)',
      borderRadius: 10, padding: '14px 16px',
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase',
        color: C.muted, marginBottom: 6,
      }}>{label}</div>
      <div style={{
        fontFamily: "'Plus Jakarta Sans', sans-serif",
        fontWeight: isText ? 600 : 800,
        fontSize: isText ? 13 : 24,
        color: accent, lineHeight: 1.2,
        wordBreak: 'break-word',
      }}>{value}</div>
    </div>
  )
}

// ── Mini stat (inline) ─────────────────────────────────────────
function MiniStat({ label, value, color = C.muted }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
    }}>
      <span style={{ color: C.muted }}>{label}:</span>
      <span style={{ color, fontWeight: 700 }}>{value}</span>
    </div>
  )
}

// ── Spinner ────────────────────────────────────────────────────
function Spinner({ text = 'Looking up...' }) {
  return (
    <div className="sg-card" style={{ textAlign: 'center', padding: '52px', marginTop: 20 }}>
      <div style={{
        width: 36, height: 36,
        border: '3px solid rgba(99,102,241,.2)', borderTopColor: C.indigo,
        borderRadius: '50%', margin: '0 auto 20px',
        animation: 'spin 0.8s linear infinite',
      }} />
      <div style={{
        fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700,
        fontSize: 16, color: C.cardText, marginBottom: 6,
      }}>{text}</div>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: C.muted,
      }}>Querying PenipuMY database...</div>
    </div>
  )
}

// ── Error box ──────────────────────────────────────────────────
function ErrorBox({ children }) {
  return (
    <div style={{
      background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
      borderRadius: 10, padding: '12px 18px', marginTop: 16,
      fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: C.red,
    }}>{children}</div>
  )
}


// ═══════════════════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════════════════
export default function ThreatIntelPage() {
  const [mode, setMode] = useState('phone')   // phone | bank | search
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  const {
    phoneResult, phoneLoading, phoneError, lookupPhone,
    bankResult, bankLoading, bankError, lookupBank,
    searchResults, searchLoading, searchError, searchScam,
    stats, statsLoading, statsError, fetchStats,
    clearResults,
  } = useThreatIntelStore()

  const loading = phoneLoading || bankLoading || searchLoading
  const error = phoneError || bankError || searchError

  useEffect(() => { fetchStats() }, [fetchStats])

  const handleSubmit = useCallback((e) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || q.length < 3) return
    clearResults()
    if (mode === 'phone') lookupPhone(q)
    else if (mode === 'bank') lookupBank(q)
    else searchScam(q)
  }, [query, mode, clearResults, lookupPhone, lookupBank, searchScam])

  const handleModeChange = (newMode) => {
    setMode(newMode)
    clearResults()
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative' }}>

      {/* Background — identical to AdminDashboard */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0 }}>
        <NeuralBackground color="#6366f1" trailOpacity={0.08} speed={0.4} particleCount={300} />
      </div>

      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header />

        <main style={{ flex: 1, width: '100%', display: 'flex', justifyContent: 'center' }}>
          <div style={{ maxWidth: 1100, width: '100%', padding: '0 24px 60px' }} className="sg-threat-shell animate-fade-up">

            {/* ── Title bar — identical pattern to AdminDashboard ── */}
            <div className="sg-threat-titlebar" style={{
              display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
              margin: '32px 0 28px', flexWrap: 'wrap', gap: 16,
            }}>
              <div>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase',
                  color: C.indigo, marginBottom: 6,
                }}>
                  External Intelligence
                </div>
                <h1 style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontSize: 28, fontWeight: 800, color: C.text, lineHeight: 1.1, margin: 0,
                }}>
                  Threat Intelligence
                </h1>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9, color: C.muted, marginTop: 6,
                }}>
                  Powered by PenipuMY — Malaysia's community-driven scam database
                </div>
              </div>

              <div className="sg-threat-actions" style={{ display: 'flex', gap: 10 }}>
                <button
                  id="back-to-scanner-btn"
                  onClick={() => navigate('/app')}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase',
                    color: C.text2,
                    background: 'var(--surface-2)',
                    border: '1px solid var(--border)',
                    borderRadius: 8, padding: '9px 18px', cursor: 'pointer',
                  }}
                >
                  Back to Scanner
                </button>
              </div>
            </div>

            {/* ── Platform Stats KPI row ── */}
            {stats && (
              <div className="sg-kpi-row" style={{ display: 'flex', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
                <KPICard
                  label="Scam Profiles"
                  value={(stats.total_profiles || 0).toLocaleString()}
                  sub="Tracked in database"
                  accent={C.red}
                />
                <KPICard
                  label="Total Reports"
                  value={(stats.total_reports || 0).toLocaleString()}
                  sub={`${(stats.verified_reports || 0).toLocaleString()} verified`}
                  accent={C.amber}
                />
                <KPICard
                  label="Total Losses"
                  value={`RM ${((stats.total_loss_myr || 0) / 1000000).toFixed(1)}M`}
                  sub="Ringgit Malaysia"
                  accent={C.red}
                />
                <KPICard
                  label="Phone Numbers"
                  value={(stats.total_phone_numbers_tracked || 0).toLocaleString()}
                  sub="Numbers tracked"
                  accent={C.indigo}
                />
              </div>
            )}
            {statsLoading && !stats && (
              <div className="sg-kpi-row" style={{ display: 'flex', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}>
                {[1,2,3,4].map(i => (
                  <div key={i} style={{
                    flex: 1, minWidth: 160, height: 100,
                    background: C.surface, borderRadius: 14,
                    border: '1px solid var(--border)',
                    animation: 'fadeIn 1s ease infinite alternate',
                  }} />
                ))}
              </div>
            )}
            {statsError && <ErrorBox>{statsError}</ErrorBox>}

            {/* ── Search Card ── */}
            <div className="sg-card sg-threat-search-card" style={{ padding: '28px 28px 24px', marginBottom: 20 }}>
              <SecLabel>Query Scam Database</SecLabel>

              {/* Mode tabs — same tab pattern as InputTabs */}
              <div className="sg-threat-mode-tabs" style={{
                display: 'flex', gap: 4, marginBottom: 20,
                background: 'var(--surface-2)', borderRadius: 10, padding: 4,
                border: '1px solid var(--border)',
              }}>
                {[
                  { key: 'phone', label: 'Phone Number' },
                  { key: 'bank', label: 'Bank Account' },
                  { key: 'search', label: 'General Search' },
                ].map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => handleModeChange(tab.key)}
                    style={{
                      flex: 1, padding: '10px 16px',
                      background: mode === tab.key ? 'var(--tab-active-bg)' : 'transparent',
                      border: mode === tab.key ? '1px solid var(--border-hi)' : '1px solid transparent',
                      borderRadius: 8, cursor: 'pointer',
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10, letterSpacing: '0.5px',
                      color: mode === tab.key ? 'var(--tab-active-text)' : 'var(--tab-inactive-text)',
                      fontWeight: mode === tab.key ? 700 : 500,
                      transition: 'all 0.2s',
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Search input */}
              <form className="sg-threat-search-form" onSubmit={handleSubmit} style={{ display: 'flex', gap: 12 }}>
                <div style={{ flex: 1, position: 'relative' }}>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={
                      mode === 'phone' ? 'Enter phone number (e.g. 0123456789)' :
                      mode === 'bank'  ? 'Enter bank account number' :
                      'Search by name, phone, account, or social handle'
                    }
                    style={{
                      width: '100%', padding: '14px 18px',
                      background: 'var(--field-bg)',
                      border: '1px solid var(--border)',
                      borderRadius: 10,
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 13, color: 'var(--text)',
                      outline: 'none',
                      transition: 'border-color 0.2s',
                    }}
                    onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,.5)'}
                    onBlur={(e) => e.target.style.borderColor = 'var(--border)'}
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || query.trim().length < 3}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase',
                    color: '#fff',
                    background: loading || query.trim().length < 3
                      ? 'rgba(99,102,241,0.25)'
                      : 'linear-gradient(135deg,#4f52c8,#6366f1)',
                    border: 'none', borderRadius: 10, padding: '14px 28px',
                    cursor: loading || query.trim().length < 3 ? 'not-allowed' : 'pointer',
                    display: 'flex', alignItems: 'center', gap: 8,
                    opacity: loading || query.trim().length < 3 ? 0.6 : 1,
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {loading && (
                    <span style={{
                      display: 'inline-block', width: 12, height: 12,
                      border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff',
                      borderRadius: '50%', animation: 'spin 0.7s linear infinite',
                    }} />
                  )}
                  {loading ? 'Searching' : 'Lookup'}
                </button>
              </form>
            </div>

            {/* ── Loading ── */}
            {loading && <Spinner text={
              mode === 'phone' ? 'Looking up phone number...' :
              mode === 'bank'  ? 'Checking bank account...' :
              'Searching scam database...'
            } />}

            {/* ── Error ── */}
            {error && <ErrorBox>{error}</ErrorBox>}

            {/* ── Results ── */}
            {phoneResult && !phoneLoading && <PhoneResultCard data={phoneResult} />}
            {bankResult && !bankLoading && <BankResultCard data={bankResult} />}
            {searchResults && !searchLoading && <SearchResultsCard data={searchResults} />}

            {/* ── Empty state ── */}
            {!loading && !error && !phoneResult && !bankResult && !searchResults && (
              <div className="sg-card" style={{
                textAlign: 'center', padding: '60px 30px', marginTop: 4,
              }}>

                <div style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  fontWeight: 700, fontSize: 18, color: C.cardText, marginBottom: 8,
                }}>
                  Query Malaysia's Scam Database
                </div>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11, color: C.muted, maxWidth: 480, margin: '0 auto', lineHeight: 1.6,
                }}>
                  Enter a phone number, bank account, or search query to check against{' '}
                  verified police reports and community-submitted scam data
                </div>
              </div>
            )}

            {/* ── Data source badge (same pattern as Admin system status bar) ── */}
            <div className="sg-card sg-status-strip" style={{
              marginTop: 20, padding: '14px 22px',
              display: 'flex', gap: 28, flexWrap: 'wrap', alignItems: 'center',
            }}>
              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 9, color: C.muted, letterSpacing: '2px', textTransform: 'uppercase',
              }}>
                Data Source
              </div>
              {[
                { label: 'PenipuMY API',  detail: 'Community Scam DB' },
                { label: 'Coverage',       detail: 'Malaysia' },
                { label: 'Data Types',     detail: 'Phone · Bank · Social' },
                { label: 'Verification',   detail: 'Police Reports + Community' },
              ].map(s => (
                <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
                    background: C.green, boxShadow: `0 0 6px ${C.green}`,
                  }} />
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: C.muted,
                  }}>
                    {s.label} — <span style={{ color: C.cardText }}>{s.detail}</span>
                  </span>
                </div>
              ))}
            </div>

          </div>
        </main>

        <Footer />
      </div>
    </div>
  )
}
