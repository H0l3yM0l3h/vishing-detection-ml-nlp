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
                background: isActive ? 'rgba(99,102,241,.15)' : 'rgba(255,255,255,.03)',
                border: `1.5px solid ${isActive ? 'rgba(99,102,241,.5)' : 'rgba(255,255,255,.08)'}`,
                backdropFilter: 'blur(12px)',
                transition: 'all .2s', textAlign: 'center',
                boxShadow: isActive ? '0 0 24px rgba(99,102,241,.1)' : 'none',
              }}
            >
              {/* Label — WHITE when active, gray when not */}
              <div style={{
                fontFamily: "'Plus Jakarta Sans', sans-serif",
                fontWeight: 600, fontSize: '14px',
                color: isActive ? '#F8FAFC' : '#5A6475',   /* WHITE active, gray inactive */
                marginBottom: '2px', transition: 'color .15s',
              }}>
                {tab.label}
              </div>
              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px', color: '#5A6475', letterSpacing: '0.5px',
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
