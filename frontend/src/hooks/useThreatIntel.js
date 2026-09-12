import { create } from 'zustand'
import api from '../api/client'

/**
 * PenipuMY threat-intelligence lookups.
 *
 * SECURITY CHANGE
 * ---------------
 * This store used to fetch the PenipuMY API key from `GET /threat-intel/key`
 * and then call `https://penipu.my/api/v1` straight from the browser whenever
 * the server-side proxy returned 403/502. That made a third-party credential
 * readable by anyone who could open DevTools — and since registration is open,
 * by anyone at all. The endpoint has been removed from the backend and the
 * direct-from-browser path is gone with it.
 *
 * Every lookup now goes through the server, which holds the key. If the
 * server's egress IP is blocked upstream, the honest answer is that the
 * lookup is unavailable — not to hand the credential to the client and ask
 * the user to disable browser security.
 */

const friendlyError = (err, fallback) => {
  const status = err.response?.status
  const detail = err.response?.data?.detail

  if (status === 503) {
    return detail || 'Threat intelligence is not configured on the server.'
  }
  if (status === 502) {
    return 'The threat intelligence provider could not be reached. Please try again shortly.'
  }
  if (status === 429) {
    return 'Too many lookups. Please wait a moment before trying again.'
  }
  return detail || fallback
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
      const res = await api.get('/threat-intel/phone', { params: { q: phoneNumber } })
      set({ phoneResult: res.data, phoneLoading: false })
    } catch (err) {
      set({
        phoneError: friendlyError(err, 'Phone lookup failed'),
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
        bankError: friendlyError(err, 'Bank lookup failed'),
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
        searchError: friendlyError(err, 'Search failed'),
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
        statsError: friendlyError(err, 'Failed to load statistics'),
        statsLoading: false,
      })
    }
  },

  clearResults: () =>
    set({
      phoneResult: null,
      phoneError: null,
      bankResult: null,
      bankError: null,
      searchResults: null,
      searchError: null,
    }),
}))
