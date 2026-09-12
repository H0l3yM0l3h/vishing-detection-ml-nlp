import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import api from '../api/client'

// Shared in-flight refresh. Module scope, not store state: this is
// concurrency control for the network layer and must not cause renders.
let inFlightRefresh = null
// Guards against hydrate() running twice on a cold load.
let hydrationStarted = false

/**
 * Authentication store.
 *
 * Session persistence
 * -------------------
 * This store previously held the token in memory only, with no `persist`
 * middleware, so pressing F5 silently logged the user out and bounced them to
 * /login. The backend has always exposed /auth/me, but nothing ever called it.
 *
 * Storage choice: sessionStorage, not localStorage. The token now survives a
 * reload (the actual bug) but does not outlive the browser tab, which keeps
 * the exposure window short on a shared or lab machine — a reasonable
 * trade-off for a security tool. Tokens are also short-lived (2h) and are
 * paired with a refresh token that rotates on every use.
 */
export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      loading: false,
      error: null,
      // Distinguishes "still restoring a saved session" from "definitely
      // logged out", so ProtectedRoute does not flash the login page.
      hydrating: true,

      login: async (username, password) => {
        set({ loading: true, error: null })
        try {
          const res = await api.post('/auth/login', { username, password })
          set({
            token: res.data.token,
            refreshToken: res.data.refresh_token || null,
            user: { username: res.data.username, role: res.data.role },
            loading: false,
            hydrating: false,
          })
          return { success: true }
        } catch (err) {
          const data = err.response?.data || {}
          set({ loading: false, error: data.detail || 'Login failed' })
          return {
            success: false,
            detail: data.detail,
            locked: data.locked,
            minutes_remaining: data.minutes_remaining,
          }
        }
      },

      register: async (username, password) => {
        set({ loading: true, error: null })
        try {
          const res = await api.post('/auth/register', { username, password })
          set({
            token: res.data.token,
            refreshToken: res.data.refresh_token || null,
            user: { username: res.data.username, role: res.data.role },
            loading: false,
            hydrating: false,
          })
          return { success: true }
        } catch (err) {
          const detail = err.response?.data?.detail || 'Registration failed'
          set({ loading: false, error: detail })
          return { success: false, detail }
        }
      },

      /**
       * Exchange the refresh token for a fresh access token.
       * Returns the new access token, or null if the session is unrecoverable.
       *
       * Concurrency: the backend ROTATES refresh tokens — using one revokes it
       * and issues a replacement. Without de-duplication, several requests
       * expiring at once (the dashboard fires /rate-limit, /history and
       * /health_detailed together on mount) each send the same refresh token.
       * The first succeeds; the rest are rejected because the token they sent
       * was just revoked, and the 401 interceptor then logs the user out —
       * destroying the perfectly valid session the first call had just
       * established.
       *
       * All concurrent callers therefore share a single in-flight request.
       */
      refreshSession: async () => {
        if (inFlightRefresh) return inFlightRefresh

        const refreshToken = get().refreshToken
        if (!refreshToken) return null

        inFlightRefresh = (async () => {
          try {
            const res = await api.post(
              '/auth/refresh',
              { refresh_token: refreshToken },
              { skipAuthRefresh: true },
            )
            set({
              token: res.data.token,
              refreshToken: res.data.refresh_token || null,
              user: { username: res.data.username, role: res.data.role },
            })
            return res.data.token
          } catch {
            return null
          } finally {
            inFlightRefresh = null
          }
        })()

        return inFlightRefresh
      },

      /**
       * Confirm a restored token is still valid, and re-read the role from the
       * server rather than trusting whatever was cached in storage.
       */
      hydrate: async () => {
        if (hydrationStarted) return
        hydrationStarted = true

        const token = get().token
        if (!token) {
          set({ hydrating: false })
          return
        }
        try {
          const res = await api.get('/auth/me', { skipAuthRefresh: true })
          set({
            user: { username: res.data.username, role: res.data.role },
            hydrating: false,
          })
        } catch {
          const refreshed = await get().refreshSession()
          if (!refreshed) {
            set({ token: null, refreshToken: null, user: null })
          }
          set({ hydrating: false })
        }
      },

      logout: () => {
        hydrationStarted = false
        inFlightRefresh = null

        // Fire the revocation before clearing local state, otherwise the
        // request goes out unauthenticated and the server cannot revoke the
        // token it was meant to revoke.
        api.post('/auth/logout').catch(() => {})
        set({ token: null, refreshToken: null, user: null, error: null, hydrating: false })
      },

      /** True when the signed-in account may view system-wide analytics. */
      isAdmin: () => get().user?.role === 'admin',

      clearError: () => set({ error: null }),
    }),
    {
      name: 'shieldguard-session',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
      onRehydrateStorage: () => (state) => {
        // Validate the restored token against the server before trusting it.
        state?.hydrate?.()
      },
    },
  ),
)
