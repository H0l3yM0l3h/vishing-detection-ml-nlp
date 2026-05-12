import { useState, useCallback } from 'react'
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
import NeuralBackground from '../components/ui/flow-field-background'
import { useAnalysisStore } from '../hooks/useAnalysis'

const STATS = [
  { val: '98.9%', label: 'ML Accuracy' },
  { val: 'SVM v3', label: 'Classifier' },
  { val: 'RAG',   label: 'Pattern DB' },
  { val: '2',     label: 'AI Reviewers' },
  { val: 'XAI',   label: 'Explainable' },
]

export default function MainDashboard() {
  const [, setInputMode] = useState('text')
  const { analyze, loading, result, error, progress } = useAnalysisStore()

  const handleTranscriptReady = useCallback(async (transcript, mode) => {
    setInputMode(mode)
    await analyze(transcript, 'SVM', mode)
  }, [analyze])

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
          <div style={{ maxWidth: '900px', width: '100%', padding: '0 24px 60px' }} className="animate-fade-up">

            <HeroSection />

            {/* Stats strip */}
            <div style={{
              display: 'flex',
              background: 'var(--surface)',
              backdropFilter: 'blur(16px)',
              border: '1px solid var(--border)',
              borderRadius: '14px',
              marginBottom: '28px',
              overflow: 'hidden',
            }}>
              {STATS.map((s, i) => (
                <div key={s.label} style={{
                  flex: 1, padding: '16px 12px', textAlign: 'center',
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
            <RateLimitBar used={0} />

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
                  Hybrid analysis typically completes in 2–5 seconds
                </div>
              </div>
            )}

            {error && <div style={{ marginTop: '24px' }}><WarnBox>{error}</WarnBox></div>}

            {result && !loading && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '28px' }} className="animate-fade-up">
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <StatusBadge source={result.source} />
                </div>

                {result.insufficient_evidence && <WarnBox>{result.insufficient_reason}</WarnBox>}
                {result.divergence_flag       && <DivergenceWarning />}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <VerdictCard verdict={result.verdict} confidence={result.confidence} source={result.source} />
                  <RiskGauge
                    confidence={result.confidence}
                    verdict={result.verdict}
                    vishingProbability={result.vishing_probability}
                  />
                </div>

                <ConfidenceBar    confidence={result.confidence} verdict={result.verdict} />
                <PhraseChips      phrases={result.suspicious_phrases} />
                <XAIPanel         keywords={result.top_keywords} />

                {result.source === 'hybrid' && (
                  <>
                    <AIAnalysisCard explanation={result.explanation} scamType={result.scam_type} />
                    <TacticChips    tactics={result.tactics} />
                    <RAGSimilarCases cases={result.similar_cases} />
                    <ActionSteps    steps={result.action_steps} />
                  </>
                )}

                {result.source === 'ml_only' && !result.insufficient_evidence && (
                  <InfoBox>AI explanation unavailable — showing ML analysis only. Check Groq API connection for full hybrid analysis.</InfoBox>
                )}

                <HighlightedTranscript html={result.highlighted_transcript} />
                <SafetyAdvice          isVishing={isVishing} />
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
