import axios from 'axios'
import { useAuthStore } from '../hooks/useAuth'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

const BACKEND_WAKEUP_MESSAGE = 'Backend is waking up, please try again in a minute.'
const DB_DOWN_MESSAGE =
  'The database is temporarily unreachable. Your work is safe — please try again in a moment.'

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config || {}

    // Cold-start handling: the Space sleeps, and the first request after that
    // times out rather than failing fast.
    const isTimeout =
      err.code === 'ECONNABORTED' || err.message?.toLowerCase().includes('timeout')
    if (isTimeout) {
      err.response = err.response || { status: 408, data: {} }
      err.response.data = { ...err.response.data, detail: BACKEND_WAKEUP_MESSAGE }
      return Promise.reject(err)
    }

    const status = err.response?.status

    // 503 = a dependency (the database) is down, not a problem with this
    // request. Say so plainly instead of showing a raw server error, and do
    // NOT log the user out — their session is still perfectly valid.
    if (status === 503) {
      err.response.data = {
        ...err.response.data,
        detail: err.response.data?.detail || DB_DOWN_MESSAGE,
      }
      return Promise.reject(err)
    }

    // 401 = the access token expired or was revoked. Try a silent refresh once
    // before giving up. Previously any 401 logged the user out immediately,
    // which with a 2-hour token means being ejected mid-task.
    if (status === 401 && !original.skipAuthRefresh && !original._retried) {
      original._retried = true
      const newToken = await useAuthStore.getState().refreshSession()
      if (newToken) {
        original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` }
        return api(original)
      }
      useAuthStore.getState().logout()
    }

    return Promise.reject(err)
  },
)

export default api
