import { create } from 'zustand'
import api from '../api/client'

export const useTranscribeStore = create((set) => ({
  loading: false,
  transcript: '',
  error: null,

  transcribe: async (audioBlob, filename = 'recording.webm') => {
    set({ loading: true, error: null, transcript: '' })
    try {
      const form = new FormData()
      form.append('file', audioBlob, filename)
      const res = await api.post('/transcribe', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      set({ loading: false, transcript: res.data.transcript })
      return res.data.transcript
    } catch (err) {
      const detail = err.response?.data?.detail || 'Transcription failed'
      set({ loading: false, error: detail })
      return null
    }
  },

  setTranscript: (text) => set({ transcript: text }),
  clearTranscript: () => set({ transcript: '', error: null }),
}))
