import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './hooks/useAuth'
import ErrorBoundary from './components/ErrorBoundary'
import LoginPage from './pages/LoginPage'
import MainDashboard from './pages/MainDashboard'
import AdminDashboard from './pages/AdminDashboard'
import ThreatIntelPage from './pages/ThreatIntelPage'

/** Full-screen placeholder shown while a saved session is being validated. */
function SessionLoading() {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        color: 'var(--text-3)',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}
    >
      Restoring session…
    </div>
  )
}

function ProtectedRoute({ children }) {
  const token = useAuthStore((s) => s.token)
  const hydrating = useAuthStore((s) => s.hydrating)

  // Without this check a page refresh renders the login screen for a frame
  // before the restored session is confirmed.
  if (hydrating) return <SessionLoading />
  if (!token) return <Navigate to="/login" replace />
  return children
}

/**
 * Route guard for system-wide analytics.
 *
 * The backend now enforces this too (/api/analytics requires role=admin), but
 * a non-admin should be told plainly rather than shown a dashboard that
 * fills with 403 errors. Client-side routing is UX; the server is the control.
 */
function AdminRoute({ children }) {
  const token = useAuthStore((s) => s.token)
  const role = useAuthStore((s) => s.user?.role)
  const hydrating = useAuthStore((s) => s.hydrating)

  if (hydrating) return <SessionLoading />
  if (!token) return <Navigate to="/login" replace />
  if (role !== 'admin') return <Navigate to="/app" replace />
  return children
}

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate)

  useEffect(() => {
    // Covers the case where the persisted store rehydrates before this
    // component mounts, so onRehydrateStorage has already fired.
    hydrate()
  }, [hydrate])

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <MainDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <AdminDashboard />
              </AdminRoute>
            }
          />
          <Route
            path="/threat-intel"
            element={
              <ProtectedRoute>
                <ThreatIntelPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
