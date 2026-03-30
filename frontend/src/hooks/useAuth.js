import { create } from 'zustand'
import api from '../api/client'

export const useAuthStore = create((set, get) => ({
  token: null,
  user: null,
  loading: false,
  error: null,

  login: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const res = await api.post('/auth/login', { username, password })
      set({
        token: res.data.token,
        user: { username: res.data.username, role: res.data.role },
        loading: false,
      })
      return { success: true }
    } catch (err) {
      const data = err.response?.data || {}
      set({
        loading: false,
        error: data.detail || 'Login failed',
      })
      return {
        success: false,
        detail: data.detail,
        locked: data.locked,
        minutes_remaining: data.minutes_remaining,
        remaining_attempts: data.remaining_attempts,
      }
    }
  },

  register: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const res = await api.post('/auth/register', { username, password })
      set({
        token: res.data.token,
        user: { username: res.data.username, role: res.data.role },
        loading: false,
      })
      return { success: true }
    } catch (err) {
      const detail = err.response?.data?.detail || 'Registration failed'
      set({ loading: false, error: detail })
      return { success: false, detail }
    }
  },

  logout: () => {
    set({ token: null, user: null, error: null })
    api.post('/auth/logout').catch(() => {})
  },

  clearError: () => set({ error: null }),
}))
