import { create } from 'zustand'
import api from '../api/client'

export const useThreatIntelStore = create((set, get) => ({
  // Phone lookup
  phoneResult: null,
  phoneLoading: false,
  phoneError: null,

  // Bank lookup
  bankResult: null,
  bankLoading: false,
  bankError: null,

  // Search
  searchResults: null,
  searchLoading: false,
  searchError: null,

  // Platform stats
  stats: null,
  statsLoading: false,
  statsError: null,

  lookupPhone: async (phoneNumber) => {
    if (get().phoneLoading) return
    set({ phoneLoading: true, phoneError: null, phoneResult: null })
    try {
      const res = await api.get('/threat-intel/phone', { params: { q: phoneNumber } })
      set({ phoneResult: res.data, phoneLoading: false })
    } catch (err) {
      set({
        phoneError: err.response?.data?.detail || 'Phone lookup failed',
        phoneLoading: false,
      })
    }
  },

  lookupBank: async (accountNumber) => {
    if (get().bankLoading) return
    set({ bankLoading: true, bankError: null, bankResult: null })
    try {
      const res = await api.get('/threat-intel/bank', { params: { q: accountNumber } })
      set({ bankResult: res.data, bankLoading: false })
    } catch (err) {
      set({
        bankError: err.response?.data?.detail || 'Bank lookup failed',
        bankLoading: false,
      })
    }
  },

  searchScam: async (query, type = 'auto') => {
    if (get().searchLoading) return
    set({ searchLoading: true, searchError: null, searchResults: null })
    try {
      const res = await api.get('/threat-intel/search', { params: { q: query, type } })
      set({ searchResults: res.data, searchLoading: false })
    } catch (err) {
      set({
        searchError: err.response?.data?.detail || 'Search failed',
        searchLoading: false,
      })
    }
  },

  fetchStats: async () => {
    if (get().statsLoading) return
    set({ statsLoading: true, statsError: null })
    try {
      const res = await api.get('/threat-intel/stats')
      set({ stats: res.data, statsLoading: false })
    } catch (err) {
      set({
        statsError: err.response?.data?.detail || 'Failed to load stats',
        statsLoading: false,
      })
    }
  },

  clearResults: () => set({
    phoneResult: null, phoneError: null,
    bankResult: null, bankError: null,
    searchResults: null, searchError: null,
  }),
}))
