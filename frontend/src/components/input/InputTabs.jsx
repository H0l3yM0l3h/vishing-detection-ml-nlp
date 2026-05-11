import { useState } from 'react'
import AudioRecorder from './AudioRecorder'
import AudioUploader from './AudioUploader'
import TranscriptInput from './TranscriptInput'

const TABS = [
  { id: 'record', label: 'Record', sub: 'Live audio' },
  { id: 'upload', label: 'Upload', sub: 'Audio file' },
  { id: 'text',   label: 'Paste',  sub: 'Transcript' },
]

export default function InputTabs({ onTranscriptReady }) {
  const [active, setActive] = useState('text')

  return (
    <div style={{ marginBottom: '24px' }}>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
        {TABS.map((tab) => {
          const isActive = active === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              style={{
                flex: 1, padding: '12px 16px', borderRadius: '12px', cursor: 'pointer',
                background: isActive ? 'var(--tab-active-bg)' : 'var(--tab-inactive-bg)',
                border: `1.5px solid ${isActive ? 'rgba(99,102,241,.55)' : 'var(--border)'}`,
                backdropFilter: 'blur(12px)',
                transition: 'all .2s', textAlign: 'center',
                boxShadow: isActive ? '0 14px 34px rgba(15,23,42,.24), inset 0 1px 0 rgba(255,255,255,.16)' : '0 10px 24px rgba(15,23,42,.08)',
              }}
            >
              {/* Label — WHITE when active, gray when not */}
              <div style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 600, fontSize: '14px',
                color: isActive ? 'var(--tab-active-text)' : 'var(--tab-inactive-text)',
                marginBottom: '2px', transition: 'color .15s',
              }}>
                {tab.label}
              </div>
              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px', color: isActive ? 'var(--tab-active-text)' : 'var(--text-3)', letterSpacing: '0.5px',
                opacity: isActive ? 0.8 : 0.72,
              }}>
                {tab.sub}
              </div>
            </button>
          )
        })}
      </div>

      {/* Panel */}
      <div className="sg-card sg-card-glow">
        {active === 'record' && <AudioRecorder  onTranscriptReady={onTranscriptReady} />}
        {active === 'upload' && <AudioUploader  onTranscriptReady={onTranscriptReady} />}
        {active === 'text'   && <TranscriptInput onTranscriptReady={onTranscriptReady} />}
      </div>
    </div>
  )
}
