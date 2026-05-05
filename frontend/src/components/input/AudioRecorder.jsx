import { useState, useRef, useCallback } from 'react'
import { useTranscribeStore } from '../../hooks/useTranscribe'
import { LiquidMetalButton } from '../ui/liquid-metal-button'

export default function AudioRecorder({ onTranscriptReady }) {
  const [recording, setRecording] = useState(false)
  const [audioUrl, setAudioUrl] = useState(null)
  const [audioBlob, setAudioBlob] = useState(null)
  const mediaRecorder = useRef(null)
  const chunks = useRef([])
  const { transcribe, loading } = useTranscribeStore()

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      chunks.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data)
      }

      recorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        setAudioBlob(blob)
        setAudioUrl(URL.createObjectURL(blob))
        stream.getTracks().forEach((t) => t.stop())
      }

      mediaRecorder.current = recorder
      recorder.start()
      setRecording(true)
    } catch (err) {
      console.error('Microphone access denied:', err)
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorder.current && recording) {
      mediaRecorder.current.stop()
      setRecording(false)
    }
  }, [recording])

  const handleTranscribe = async () => {
    if (!audioBlob) return
    const text = await transcribe(audioBlob, 'recording.webm')
    if (text) onTranscriptReady(text, 'record')
  }

  return (
    <div className="space-y-4">
      <div className="sec-label">Voice Capture</div>

      <div className="flex items-center gap-4">
        {!recording ? (
          <button
            onClick={startRecording}
            className="flex items-center gap-2 font-display text-[10px] font-bold tracking-[3px] uppercase
              text-white px-6 py-3 rounded-lg cursor-pointer border-none"
            style={{
              background: 'linear-gradient(135deg, #b81530, #801020)',
              boxShadow: '0 4px 16px rgba(232,32,60,.28)',
            }}
          >
            <span className="w-2.5 h-2.5 rounded-full bg-white" />
            START RECORDING
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="flex items-center gap-2 font-display text-[10px] font-bold tracking-[3px] uppercase
              text-white px-6 py-3 rounded-lg cursor-pointer border-none animate-rec-pulse"
            style={{ background: 'var(--red)' }}
          >
            <span className="w-2.5 h-2.5 rounded-sm bg-white" />
            STOP RECORDING
          </button>
        )}

        {recording && (
          <span className="font-mono text-[10px] text-[var(--red)] tracking-wider animate-blink">
            RECORDING...
          </span>
        )}
      </div>

      {/* Playback */}
      {audioUrl && (
        <div className="space-y-3">
          <audio src={audioUrl} controls className="w-full h-10" style={{ filter: 'invert(1) hue-rotate(180deg)' }} />
          <LiquidMetalButton
            label={loading ? 'Transcribing...' : 'Transcribe Audio'}
            onClick={handleTranscribe}
            disabled={!audioBlob || loading}
            loading={loading}
            fullWidth
          />
        </div>
      )}
    </div>
  )
}

