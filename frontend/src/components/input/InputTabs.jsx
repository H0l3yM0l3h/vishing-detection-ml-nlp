import { useState } from 'react'
import AudioRecorder from './AudioRecorder'
import AudioUploader from './AudioUploader'
import TranscriptInput from './TranscriptInput'

const TABS = [
  { id: 'record', label: 'Record Audio', num: '01' },
  { id: 'upload', label: 'Upload File', num: '02' },
  { id: 'text', label: 'Paste Transcript', num: '03' },
]

export default function InputTabs({ onTranscriptReady }) {
  const [active, setActive] = useState('text')

  return (
    <div className="space-y-5">
      {/* Tab buttons */}
      <div className="flex gap-3">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`flex-1 sg-card !p-4 text-center transition-all cursor-pointer border
              ${active === tab.id
                ? 'border-[rgba(0,170,255,.4)] shadow-[0_0_18px_rgba(0,170,255,.08)]'
                : 'border-[var(--border)] hover:border-[rgba(0,170,255,.2)]'
              }`}
            style={{ background: 'var(--c1)' }}
          >
            <div className="font-display text-2xl font-black text-[var(--blue)] opacity-30 leading-none mb-1">
              {tab.num}
            </div>
            <div className="font-bold text-xs text-[var(--text)] tracking-wider uppercase">{tab.label}</div>
          </button>
        ))}
      </div>

      {/* Active panel */}
      <div className="sg-card sg-card-glow">
        {active === 'record' && <AudioRecorder onTranscriptReady={onTranscriptReady} />}
        {active === 'upload' && <AudioUploader onTranscriptReady={onTranscriptReady} />}
        {active === 'text' && <TranscriptInput onTranscriptReady={onTranscriptReady} />}
      </div>
    </div>
  )
}
