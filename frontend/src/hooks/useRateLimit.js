import { create } from 'zustand'
import api from '../api/client'

export const useRateLimitStore = create((set) => ({
  used: 0,
  max: 30,
  remaining: 30,
  allowed: true,
  loading: false,
  error: null,

  fetchUsage: async () => {
    set({ loading: true, error: null })
    try {
      const res = await api.get('/rate-limit')
      set({
        used: Number(res.data.used || 0),
        max: Number(res.data.max || 30),
        remaining: Number(res.data.remaining || 0),
        allowed: Boolean(res.data.allowed),
        loading: false,
        error: null,
      })
      return res.data
    } catch (err) {
      const detail = err.response?.data?.detail || 'Unable to load scan usage'
      set({ loading: false, error: detail })
      return null
    }
  },
}))
