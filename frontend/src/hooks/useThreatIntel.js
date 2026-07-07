import { create } from 'zustand'
import axios from 'axios'
import api from '../api/client'

// Helper to check if error indicates a proxy/server block
const isServerBlock = (err) => {
  const detail = err.response?.data?.detail || ''
  return (
    err.response?.status === 502 ||
    err.response?.status === 403 ||
    detail.includes('403') ||
    detail.includes('Forbidden')
  )
}

// Fetch the API key from backend
const getApiKey = async () => {
  try {
    const res = await api.get('/threat-intel/key')
    return res.data.key
  } catch {
    return null
  }
}

// Perform direct query from browser to PenipuMY
const directQuery = async (endpoint, params = {}, apiKey) => {
  const key = apiKey || await getApiKey()
  if (!key) throw new Error('PenipuMY API key not configured on server')

  // Run call directly from client browser
  const res = await axios.get(`https://penipu.my/api/v1${endpoint}`, {
    params,
    headers: {
      'X-API-Key': key,
      'Accept': 'application/json',
    }
  })
  return res.data
}

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
      // Try backend proxy first
      const res = await api.get('/threat-intel/phone', { params: { q: phoneNumber } })
      set({ phoneResult: res.data, phoneLoading: false })
    } catch (err) {
      let finalErr = err
      if (isServerBlock(err)) {
        // Fallback: Direct browser fetch
        try {
          const data = await directQuery('/phone', { q: phoneNumber })
          set({ phoneResult: data, phoneLoading: false })
          return
        } catch (directErr) {
          finalErr = directErr
        }
      }
      set({
        phoneError: finalErr.response?.data?.detail || finalErr.message || 'Phone lookup failed',
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
      let finalErr = err
      if (isServerBlock(err)) {
        try {
          const data = await directQuery('/bank', { q: accountNumber })
          set({ bankResult: data, bankLoading: false })
          return
        } catch (directErr) {
          finalErr = directErr
        }
      }
      set({
        bankError: finalErr.response?.data?.detail || finalErr.message || 'Bank lookup failed',
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
      let finalErr = err
      if (isServerBlock(err)) {
        try {
          const data = await directQuery('/search', { q: query, type })
          set({ searchResults: data, searchLoading: false })
          return
        } catch (directErr) {
          finalErr = directErr
        }
      }
      set({
        searchError: finalErr.response?.data?.detail || finalErr.message || 'Search failed',
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
      let finalErr = err
      if (isServerBlock(err)) {
        try {
          const data = await directQuery('/stats')
          set({ stats: data, statsLoading: false })
          return
        } catch (directErr) {
          // If it fails (possibly due to CORS), show a clean custom instruction
          if (directErr.message?.includes('Network Error')) {
             set({
               statsError: 'Hugging Face server IP is blocked by PenipuMY firewall. Please enable a CORS extension or query using Localhost.',
               statsLoading: false
             })
             return
          }
          finalErr = directErr
        }
      }
      set({
        statsError: finalErr.response?.data?.detail || finalErr.message || 'Failed to load stats',
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
