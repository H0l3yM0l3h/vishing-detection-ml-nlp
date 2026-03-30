import { create } from 'zustand'
import api from '../api/client'

export const useAnalysisStore = create((set) => ({
  loading: false,
  result: null,
  error: null,
  progress: '',

  analyze: async (transcript, modelChoice, inputMode) => {
    set({ loading: true, error: null, result: null, progress: 'Running ML analysis...' })
    try {
      // Update progress stages
      const progressTimer = setTimeout(() => {
        set({ progress: 'Querying scam database...' })
      }, 3000)

      const progressTimer2 = setTimeout(() => {
        set({ progress: 'AI agents reasoning...' })
      }, 8000)

      const progressTimer3 = setTimeout(() => {
        set({ progress: 'Generating verdict...' })
      }, 20000)

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
      const detail = err.response?.data?.detail || 'Analysis failed'
      set({ loading: false, error: detail, progress: '' })
      return null
    }
  },

  clearResult: () => set({ result: null, error: null, progress: '' }),
}))
