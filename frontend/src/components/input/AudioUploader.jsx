import { useState, useRef, useId } from 'react'
import { useTranscribeStore } from '../../hooks/useTranscribe'
import { Label } from '../ui/label'
import { LiquidMetalButton } from '../ui/liquid-metal-button'
import { Upload } from 'lucide-react'

const ALLOWED = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.webm']
const MAX_SIZE = 25 * 1024 * 1024

export default function AudioUploader({ onTranscriptReady }) {
  const [file,  setFile]  = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef()
  const id = useId()
  const { transcribe, loading } = useTranscribeStore()

  const handleFile = (f) => {
    setError(null)
    const ext = '.' + f.name.split('.').pop().toLowerCase()
    if (!ALLOWED.includes(ext)) {
      setError(`Unsupported format ${ext}. Accepted: ${ALLOWED.join(', ')}`)
      return
    }
    if (f.size > MAX_SIZE) { setError('File too large (max 25 MB)'); return }
    setFile(f)
  }

  const handleUpload = async () => {
    if (!file) return
    const text = await transcribe(file, file.name)
    if (text) onTranscriptReady(text, 'upload')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div className="sec-label">Upload Audio File</div>

      {/* Styled file input row */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <Label htmlFor={id} style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#a1a1aa' }}>
          Select file
        </Label>
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept={ALLOWED.join(',')}
          onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
          style={{ display: 'none' }}
        />
        {/* Custom styled trigger */}
        <div
          onClick={() => !loading && inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); e.dataTransfer.files[0] && handleFile(e.dataTransfer.files[0]) }}
          style={{
            display: 'flex', alignItems: 'center', gap: '12px',
            padding: '0', borderRadius: '10px', overflow: 'hidden',
            border: '1px solid #27272a', cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'border-color .2s',
          }}
          onMouseEnter={(e) => { if (!loading) e.currentTarget.style.borderColor = '#3f3f46' }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#27272a' }}
        >
          {/* File button area */}
          <div style={{
            padding: '10px 14px', background: '#18181b', borderRight: '1px solid #27272a',
            display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0,
          }}>
            <Upload size={14} style={{ color: '#6366f1' }} />
            <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', fontWeight: 500, color: '#a1a1aa', whiteSpace: 'nowrap' }}>
              Choose file
            </span>
          </div>
          {/* File name area */}
          <span style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: '12px',
            color: file ? '#f4f4f5' : '#52525b', paddingRight: '12px',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {file ? file.name : 'No file selected'}
          </span>
          {file && (
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#52525b', marginLeft: 'auto', paddingRight: '12px', flexShrink: 0 }}>
              {(file.size / 1024 / 1024).toFixed(1)} MB
            </span>
          )}
        </div>
        <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#3f3f46', letterSpacing: '0.5px' }}>
          WAV, MP3, M4A, OGG, FLAC, WEBM — max 25 MB — drag and drop supported
        </p>
      </div>

      {error && (
        <div style={{ background: 'rgba(239,68,68,.07)', border: '1px solid rgba(239,68,68,.2)', borderRadius: '8px', padding: '10px 14px', fontSize: '13px', color: '#FCA5A5', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
          {error}
        </div>
      )}

      {file && (
        <LiquidMetalButton
          label={loading ? 'Transcribing...' : 'Upload and Transcribe'}
          onClick={handleUpload}
          disabled={loading}
          loading={loading}
          fullWidth
        />
      )}
    </div>
  )
}
