import axios from 'axios'
import { useAuthStore } from '../hooks/useAuth'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

const BACKEND_WAKEUP_MESSAGE = 'Backend is waking up, please try again in a minute.'

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isTimeout = err.code === 'ECONNABORTED' || err.message?.toLowerCase().includes('timeout')
    if (isTimeout) {
      err.response = err.response || { status: 408, data: {} }
      err.response.data = {
        ...err.response.data,
        detail: BACKEND_WAKEUP_MESSAGE,
      }
    }

    if (err.response?.status === 401) {
      const { logout } = useAuthStore.getState()
      logout()
    }
    return Promise.reject(err)
  }
)

export default api
