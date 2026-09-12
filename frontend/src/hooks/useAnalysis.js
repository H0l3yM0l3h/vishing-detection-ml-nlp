import { create } from 'zustand'
import api from '../api/client'

export const useAnalysisStore = create((set, get) => ({
  loading: false,
  result: null,
  error: null,
  progress: '',

  analyze: async (transcript, modelChoice, inputMode) => {
    // ── Guard: prevent duplicate concurrent submissions ──
    if (get().loading) return null

    set({ loading: true, error: null, result: null, progress: 'Classifying with the ML model...' })

    const progressTimer = setTimeout(() => {
      set({ progress: 'Matching against known scam calls...' })
    }, 3000)

    const progressTimer2 = setTimeout(() => {
      set({ progress: 'Checking numbers and accounts...' })
    }, 8000)

    const progressTimer3 = setTimeout(() => {
      set({ progress: 'AI review in progress...' })
    }, 15000)

    try {
      const res = await api.post('/analyze', {
        transcript,
        model_choice: modelChoice,
        input_mode: inputMode,
      })

      clearTimeout(progressTimer)
      clearTimeout(progressTimer2)
      clearTimeout(progressTimer3)

      set({ loading: false, result: res.data, progress: '' })
      return res.data
    } catch (err) {
      clearTimeout(progressTimer)
      clearTimeout(progressTimer2)
      clearTimeout(progressTimer3)

      const detail = err.response?.data?.detail || 'Analysis failed'
      set({ loading: false, error: detail, progress: '' })
      return null
    }
  },

  clearResult: () => set({ result: null, error: null, progress: '' }),
}))
