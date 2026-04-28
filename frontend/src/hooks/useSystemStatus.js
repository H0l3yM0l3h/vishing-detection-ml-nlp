import { useState, useEffect, useCallback } from 'react'

const POLL_MS = 30_000   // check every 30 seconds
const TIMEOUT_MS = 5_000 // consider offline if no response in 5s

/**
 * useSystemStatus — polls /api/health every 30s.
 * Returns:
 *   connected   : bool   — backend reachable
 *   status      : 'online' | 'degraded' | 'offline'
 *   components  : object  — per-component ok/detail map
 *   lastChecked : Date | null
 *   checking    : bool
 */
export function useSystemStatus() {
  const [state, setState] = useState({
    connected:   null,   // null = initial unknown
    status:      'checking',
    components:  {},
    lastChecked: null,
    checking:    true,
  })

  const check = useCallback(async () => {
    setState((s) => ({ ...s, checking: true }))
    try {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)

      const res = await fetch('/api/health_detailed', { signal: controller.signal })
      clearTimeout(timer)

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      setState({
        connected:   true,
        status:      data.status,          // 'online' | 'degraded'
        components:  data.components || {},
        lastChecked: new Date(),
        checking:    false,
      })
    } catch {
      setState({
        connected:   false,
        status:      'offline',
        components:  {},
        lastChecked: new Date(),
        checking:    false,
      })
    }
  }, [])

  useEffect(() => {
    check()
    const id = setInterval(check, POLL_MS)
    return () => clearInterval(id)
  }, [check])

  return state
}
