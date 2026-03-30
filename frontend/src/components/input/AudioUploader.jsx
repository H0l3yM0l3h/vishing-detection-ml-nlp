import { useState, useRef } from 'react'
import { useTranscribeStore } from '../../hooks/useTranscribe'

const ALLOWED = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.webm']
const MAX_SIZE = 25 * 1024 * 1024

export default function AudioUploader({ onTranscriptReady }) {
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef()
  const { transcribe, loading } = useTranscribeStore()

  const handleFile = (f) => {
    setError(null)
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!ALLOWED.includes(ext)) {
      setError(`Unsupported format: ${ext}. Use ${ALLOWED.join(', ')}`)
      return
    }
    if (f.size > MAX_SIZE) {
      setError('File too large (max 25MB)')
      return
    }
    setFile(f)
  }

  const handleUpload = async () => {
    if (!file) return
    const text = await transcribe(file, file.name)
    if (text) onTranscriptReady(text, 'upload')
  }

  return (
    <div className="space-y-4">
      <div className="sec-label">Upload Audio File</div>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); handleFile(e.dataTransfer.files[0]) }}
        className="border-2 border-dashed border-[var(--border)] rounded-lg p-8 text-center cursor-pointer
          hover:border-[rgba(0,170,255,.3)] transition-colors"
      >
        <div className="font-display text-lg text-[var(--muted)] mb-2">DROP AUDIO FILE HERE</div>
        <div className="font-mono text-[10px] text-[var(--muted)] tracking-wider">
          WAV, MP3, M4A, OGG, FLAC, WEBM (max 25MB)
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED.join(',')}
          className="hidden"
          onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
        />
      </div>

      {error && (
        <div className="text-sm text-[var(--red)]">{error}</div>
      )}

      {file && (
        <div className="flex items-center justify-between sg-card !p-3">
          <span className="font-mono text-xs text-[var(--text)]">{file.name}</span>
          <span className="font-mono text-[10px] text-[var(--muted)]">
            {(file.size / 1024 / 1024).toFixed(1)} MB
          </span>
        </div>
      )}

      {file && (
        <button
          onClick={handleUpload}
          disabled={loading}
          className="w-full font-display text-[10px] font-bold tracking-[3px] uppercase text-white
            py-3 rounded-lg cursor-pointer border-none disabled:opacity-50"
          style={{
            background: 'linear-gradient(135deg, #0066bb, #004488)',
            boxShadow: '0 4px 16px rgba(0,170,255,.2)',
          }}
        >
          {loading ? 'TRANSCRIBING...' : 'UPLOAD & TRANSCRIBE'}
        </button>
      )}
    </div>
  )
}
