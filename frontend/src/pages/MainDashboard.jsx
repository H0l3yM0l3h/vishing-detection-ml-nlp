import { useState, useCallback } from 'react'
import Header from '../components/layout/Header'
import Footer from '../components/layout/Footer'
import HeroSection from '../components/dashboard/HeroSection'
import StepGuide from '../components/dashboard/StepGuide'
import RateLimitBar from '../components/dashboard/RateLimitBar'
import ScanHistory from '../components/dashboard/ScanHistory'
import InputTabs from '../components/input/InputTabs'
import ModelSelector from '../components/ui/ModelSelector'
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
import { useAnalysisStore } from '../hooks/useAnalysis'

export default function MainDashboard() {
  const [modelChoice, setModelChoice] = useState('SVM')
  const [inputMode, setInputMode] = useState('text')
  const { analyze, loading, result, error, progress } = useAnalysisStore()

  const handleTranscriptReady = useCallback(async (transcript, mode) => {
    setInputMode(mode)
    await analyze(transcript, modelChoice, mode)
  }, [modelChoice, analyze])

  const isVishing = result?.verdict?.toLowerCase().includes('vishing') ||
    result?.verdict?.toLowerCase().includes('hang up')

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="max-w-[900px] mx-auto px-6 py-10 animate-fade-up">
          <HeroSection />

          {/* Stats strip */}
          <div className="flex justify-center gap-4 mb-8 flex-wrap">
            {[
              ['98.5%', 'ML Accuracy'],
              ['4+1', 'ML + LLM'],
              ['RAG', 'Pattern DB'],
              ['4', 'AI Agents'],
              ['XAI', 'Explainable'],
            ].map(([val, label]) => (
              <div key={label} className="sg-card !p-3 text-center min-w-[100px]">
                <div className="font-display text-lg font-bold text-[var(--blue)]">{val}</div>
                <div className="font-mono text-[9px] text-[var(--muted)] tracking-[2px] uppercase mt-0.5">{label}</div>
              </div>
            ))}
          </div>

          <StepGuide />
          <RateLimitBar used={0} />

          {/* Model selector */}
          <div className="mb-6">
            <ModelSelector value={modelChoice} onChange={setModelChoice} />
          </div>

          {/* Input */}
          <InputTabs onTranscriptReady={handleTranscriptReady} />

          {/* Loading state */}
          {loading && (
            <div className="sg-card text-center py-10 mt-8">
              <div className="inline-block w-10 h-10 border-2 border-[var(--blue)] border-t-transparent rounded-full mb-4"
                style={{ animation: 'spin 1s linear infinite' }} />
              <div className="font-display text-sm text-[var(--blue)] tracking-[3px] uppercase">
                {progress || 'Processing...'}
              </div>
              <div className="font-mono text-[10px] text-[var(--muted)] mt-2 tracking-wider">
                Please wait — hybrid analysis may take 30-90 seconds
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mt-8">
              <WarnBox>{error}</WarnBox>
            </div>
          )}

          {/* Results */}
          {result && !loading && (
            <div className="space-y-5 mt-8 animate-fade-up">
              {/* Source badge */}
              <div className="flex justify-center">
                <StatusBadge source={result.source} />
              </div>

              {/* Insufficient evidence */}
              {result.insufficient_evidence && (
                <WarnBox>{result.insufficient_reason}</WarnBox>
              )}

              {/* Divergence warning */}
              {result.divergence_flag && <DivergenceWarning />}

              {/* Main verdict + gauge */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <VerdictCard
                  verdict={result.verdict}
                  confidence={result.confidence}
                  source={result.source}
                />
                <RiskGauge confidence={result.confidence} />
              </div>

              <ConfidenceBar confidence={result.confidence} />

              {/* Phrases */}
              <PhraseChips phrases={result.suspicious_phrases} />

              {/* XAI */}
              <XAIPanel keywords={result.top_keywords} />

              {/* AI Analysis (Phase 2 hybrid only) */}
              {result.source === 'hybrid' && (
                <>
                  <AIAnalysisCard
                    explanation={result.explanation}
                    scamType={result.scam_type}
                  />
                  <TacticChips tactics={result.tactics} />
                  <RAGSimilarCases cases={result.similar_cases} />
                  <ActionSteps steps={result.action_steps} />
                </>
              )}

              {/* ML-only fallback info */}
              {result.source === 'ml_only' && !result.insufficient_evidence && (
                <InfoBox>
                  AI explanation unavailable — showing ML analysis only. Start Ollama for full hybrid analysis.
                </InfoBox>
              )}

              {/* Highlighted transcript */}
              <HighlightedTranscript html={result.highlighted_transcript} />

              {/* Safety advice */}
              <SafetyAdvice isVishing={isVishing} />
            </div>
          )}

          <ScanHistory />
        </div>
      </main>

      <Footer />
    </div>
  )
}
