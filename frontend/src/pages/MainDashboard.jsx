import { useEffect, useState, useCallback } from 'react'
import Header from '../components/layout/Header'
import Footer from '../components/layout/Footer'
import HeroSection from '../components/dashboard/HeroSection'
import StepGuide from '../components/dashboard/StepGuide'
import RateLimitBar from '../components/dashboard/RateLimitBar'
import ScanHistory from '../components/dashboard/ScanHistory'
import SystemDiagnostics from '../components/dashboard/SystemDiagnostics'
import InputTabs from '../components/input/InputTabs'
import StatusBadge from '../components/ui/StatusBadge'
import InfoBox from '../components/ui/InfoBox'
import WarnBox from '../components/ui/WarnBox'
import VerdictCard from '../components/results/VerdictCard'
import ConfidenceBar from '../components/results/ConfidenceBar'
import RiskGauge from '../components/results/RiskGauge'
import PhraseChips from '../components/results/PhraseChips'
import HighlightedTranscript from '../components/results/HighlightedTranscript'
import XAIPanel from '../components/results/XAIPanel'
import AIAnalysisCard from '../components/results/AIAnalysisCard'
import TacticChips from '../components/results/TacticChips'
import RAGSimilarCases from '../components/results/RAGSimilarCases'
import ActionSteps from '../components/results/ActionSteps'
import SafetyAdvice from '../components/results/SafetyAdvice'
import DivergenceWarning from '../components/results/DivergenceWarning'
import InjectionWarning from '../components/results/InjectionWarning'
import ExtractedIntelPanel from '../components/results/ExtractedIntelPanel'
import SignalConvergence from '../components/results/SignalConvergence'
import NeuralBackground from '../components/ui/flow-field-background'
import { useAnalysisStore } from '../hooks/useAnalysis'
import { useRateLimitStore } from '../hooks/useRateLimit'

const STATS = [
  // 98.88% clean-test accuracy, from models/svm_model_metadata.json.
  // HeroSection previously claimed 99.4% on the same page.
  { val: '98.9%', label: 'ML Accuracy' },
  { val: 'SVM v3', label: 'Classifier' },
  { val: 'RAG',   label: 'Pattern DB' },
  { val: '2',     label: 'AI Reviewers' },
  { val: 'XAI',   label: 'Explainable' },
]

/**
 * A labelled group of result panels.
 *
 * Reuses the established `.sec-label` treatment — mono, tracked, with the
 * hairline rule that fades to the right — which is already the app's way of
 * introducing a block. The section itself contributes only rhythm: a wide gap
 * above it to separate tiers, and a tighter gap between the panels inside it
 * so they read as one group rather than four unrelated cards.
 */
function ResultSection({ title, children }) {
  return (
    <section style={{ marginTop: '36px' }}>
      <h2 className="sec-label" style={{ marginBottom: '14px', fontWeight: 400 }}>
        {title}
      </h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {children}
      </div>
    </section>
  )
}

export default function MainDashboard() {
  const [, setInputMode] = useState('text')
  const { analyze, loading, result, error, progress } = useAnalysisStore()
  const {
    used: scanUsed,
    max: scanMax,
    loading: scanUsageLoading,
    fetchUsage,
  } = useRateLimitStore()

  useEffect(() => {
    fetchUsage()
  }, [fetchUsage])

  const handleTranscriptReady = useCallback(async (transcript, mode) => {
    setInputMode(mode)
    await analyze(transcript, 'SVM', mode)
    await fetchUsage()
  }, [analyze, fetchUsage])

  const isVishing = result?.verdict?.toLowerCase().includes('vishing') || result?.verdict?.toLowerCase().includes('hang up')
  const isSafe    = result?.verdict?.toLowerCase().includes('safe')    || result?.verdict?.toLowerCase().includes('legitimate')
  const threatClass = result && !loading ? (isVishing ? 'threat-vishing' : isSafe ? 'threat-safe' : '') : ''

  return (
    <div className={`min-h-screen flex flex-col w-full relative ${threatClass}`} style={{ transition: 'box-shadow 0.8s ease' }}>

      {/* Fixed flow field background — fills entire viewport */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0 }}>
        <NeuralBackground
          color="#6366f1"
          trailOpacity={0.12}
          speed={0.7}
          particleCount={450}
        />
      </div>

      {/* All content above the background */}
      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Header />

        <main style={{ flex: 1, width: '100%', display: 'flex', justifyContent: 'center' }}>
          <div style={{ maxWidth: '900px', width: '100%', padding: '0 24px 60px' }} className="sg-dashboard-shell animate-fade-up">

            <HeroSection />

            {/* Stats strip */}
            <div className="sg-stats-strip" style={{
              display: 'flex',
              overflowX: 'auto',
              WebkitOverflowScrolling: 'touch',
              background: 'var(--surface)',
              backdropFilter: 'blur(16px)',
              border: '1px solid var(--border)',
              borderRadius: '14px',
              marginBottom: '28px',
              overflowY: 'hidden',
            }}>
              {STATS.map((s, i) => (
                <div key={s.label} className="sg-stat-item" style={{
                  flex: '1 0 130px', padding: '16px 12px', textAlign: 'center',
                  borderRight: i < STATS.length - 1 ? '1px solid var(--border)' : 'none',
                }}>
                  {/* Value is WHITE, not purple */}
                  <div style={{
                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                    fontWeight: 800, fontSize: '18px', color: 'var(--text)',
                  }}>
                    {s.val}
                  </div>
                  <div style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '9px', color: 'var(--text-3)',
                    letterSpacing: '1px', textTransform: 'uppercase', marginTop: '3px',
                  }}>
                    {s.label}
                  </div>
                </div>
              ))}
            </div>

            <StepGuide />
            <RateLimitBar used={scanUsed} max={scanMax} loading={scanUsageLoading} />

            <InputTabs onTranscriptReady={handleTranscriptReady} />

            {/* Loading */}
            {loading && (
              <div className="sg-card" style={{ textAlign: 'center', padding: '52px', marginTop: '24px' }}>
                <div style={{
                  width: '36px', height: '36px',
                  border: '3px solid rgba(99,102,241,.2)', borderTopColor: '#6366F1',
                  borderRadius: '50%', margin: '0 auto 20px',
                  animation: 'spin 0.8s linear infinite',
                }} />
                <div style={{
                  fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700,
                  fontSize: '16px', color: 'var(--text)', marginBottom: '6px',
                }}>
                  {progress || 'Analysing transcript...'}
                </div>
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--text-3)',
                }}>
                  ML classification is instant; the AI review layer usually takes 5–20 seconds
                </div>
              </div>
            )}

            {error && <div style={{ marginTop: '24px' }}><WarnBox>{error}</WarnBox></div>}

            {result && !loading && (
              /*
                Results are grouped into four tiers rather than presented as
                one flat stack. Previously fourteen panels sat at an identical
                16px gap with identical visual weight, so the verdict — the
                one thing the user came for — competed for attention with the
                RAG similar-cases list.

                The hierarchy is expressed only through spacing and grouping:
                wide gaps BETWEEN tiers, tight gaps WITHIN them. No new
                colours, typefaces or card styles are introduced.
              */
              <div style={{ marginTop: '32px' }} className="animate-fade-up">

                {/* ── Tier 0: interrupts ──
                    Things that change how the rest should be read. They come
                    before the verdict because they qualify it. */}
                {(result.insufficient_evidence ||
                  result.divergence_flag ||
                  result.prompt_injection?.detected) && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '28px' }}>
                    {result.insufficient_evidence && <WarnBox>{result.insufficient_reason}</WarnBox>}
                    {result.divergence_flag       && <DivergenceWarning />}
                    <InjectionWarning injection={result.prompt_injection} />
                  </div>
                )}

                {/* ── Tier 1: the answer ── */}
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '14px' }}>
                  <StatusBadge source={result.source} />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2" style={{ gap: '16px' }}>
                  <VerdictCard verdict={result.verdict} confidence={result.confidence} source={result.source} />
                  <RiskGauge
                    confidence={result.confidence}
                    verdict={result.verdict}
                    vishingProbability={result.vishing_probability}
                  />
                </div>

                <div style={{ marginTop: '12px' }}>
                  <ConfidenceBar confidence={result.confidence} verdict={result.verdict} />
                </div>

                {/* Makes the hybrid architecture legible: which independent
                    layers ran, and which of them found something. */}
                <div style={{ marginTop: '12px' }}>
                  <SignalConvergence result={result} />
                </div>

                {/* ── Tier 2: evidence ── */}
                <ResultSection title="Evidence">
                  <ExtractedIntelPanel intel={result.extracted_intel} />
                  <PhraseChips phrases={result.suspicious_phrases} />
                  <XAIPanel    keywords={result.top_keywords} />

                  {result.source === 'hybrid' && (
                    <>
                      <AIAnalysisCard explanation={result.explanation} scamType={result.scam_type} />
                      <TacticChips    tactics={result.tactics} />
                      <RAGSimilarCases cases={result.similar_cases} />
                    </>
                  )}

                  {result.source === 'ml_only' && !result.insufficient_evidence && (
                    <InfoBox>AI explanation unavailable — showing ML analysis only. Check Groq API connection for full hybrid analysis.</InfoBox>
                  )}
                </ResultSection>

                {/* ── Tier 3: what to do ── */}
                <ResultSection title="What to do next">
                  {result.source === 'hybrid' && <ActionSteps steps={result.action_steps} />}
                  <SafetyAdvice isVishing={isVishing} />
                </ResultSection>

                {/* ── Tier 4: reference ── */}
                <ResultSection title="The call, annotated">
                  <HighlightedTranscript html={result.highlighted_transcript} />
                </ResultSection>
              </div>
            )}

            <ScanHistory />
            <SystemDiagnostics />
          </div>
        </main>

        <Footer />
      </div>
    </div>
  )
}
