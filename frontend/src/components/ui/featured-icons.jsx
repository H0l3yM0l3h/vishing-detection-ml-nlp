import { isValidElement } from 'react'

/**
 * FeaturedIcon — adapted from Untitled UI to JSX with inline styles.
 * Tokens replaced with explicit hex/rgba values matching ShieldGuard theme.
 * Supported themes: 'outline' | 'dark' | 'light'
 * Supported colors: 'brand' (indigo) | 'success' (green) | 'error' (red) | 'warning' (amber) | 'gray'
 */

const sizes = {
  sm: { icon: 16, mid: 24, outer: 34 },
  md: { icon: 20, mid: 28, outer: 38 },
  lg: { icon: 24, mid: 32, outer: 42 },
  xl: { icon: 28, mid: 36, outer: 48 },
}

const borderRadius = {
  sm: { dark: '6px',  light: '50%', outline: '50%' },
  md: { dark: '8px',  light: '50%', outline: '50%' },
  lg: { dark: '10px', light: '50%', outline: '50%' },
  xl: { dark: '12px', light: '50%', outline: '50%' },
}

const palette = {
  brand:   { solid: '#6366f1', mid: 'rgba(99,102,241,.28)',  outer: 'rgba(99,102,241,.10)', light: 'rgba(99,102,241,.12)',  text: '#818cf8' },
  success: { solid: '#10B981', mid: 'rgba(16,185,129,.28)',  outer: 'rgba(16,185,129,.10)', light: 'rgba(16,185,129,.12)',  text: '#34d399' },
  error:   { solid: '#EF4444', mid: 'rgba(239,68,68,.28)',   outer: 'rgba(239,68,68,.10)',  light: 'rgba(239,68,68,.12)',   text: '#f87171' },
  warning: { solid: '#F59E0B', mid: 'rgba(245,158,11,.28)',  outer: 'rgba(245,158,11,.10)', light: 'rgba(245,158,11,.12)',  text: '#fbbf24' },
  gray:    { solid: '#3f3f46', mid: 'rgba(255,255,255,.12)', outer: 'rgba(255,255,255,.05)', light: 'rgba(255,255,255,.06)', text: '#a1a1aa' },
}

function isReactComponent(val) {
  if (!val) return false
  if (typeof val === 'function') return true
  if (typeof val === 'object' && val !== null && val.$$typeof) return true
  return false
}

export function FeaturedIcon({
  icon: Icon,
  size  = 'md',
  color = 'brand',
  theme = 'outline',
  style = {},
  children,
}) {
  const sz  = sizes[size]
  const c   = palette[color]
  const br  = borderRadius[size][theme] ?? '50%'

  // ── Outline: three concentric rings ──────────────────
  if (theme === 'outline') {
    return (
      <div style={{
        position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: sz.outer, height: sz.outer, flexShrink: 0, ...style,
      }}>
        {/* Outer ring */}
        <div style={{
          position: 'absolute', inset: 0, borderRadius: '50%',
          border: `2px solid ${c.outer}`,
        }} />
        {/* Middle ring */}
        <div style={{
          position: 'absolute',
          width: sz.mid, height: sz.mid, borderRadius: '50%',
          border: `2px solid ${c.mid}`,
        }} />
        {/* Icon */}
        <div style={{ position: 'relative', zIndex: 1, color: c.text, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {isReactComponent(Icon)
            ? <Icon size={sz.icon} strokeWidth={2} />
            : isValidElement(Icon)
              ? Icon
              : null}
          {children}
        </div>
      </div>
    )
  }

  // ── Dark: solid rounded square ──────────────────
  if (theme === 'dark') {
    return (
      <div style={{
        position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: sz.mid, height: sz.mid, borderRadius: br, flexShrink: 0,
        background: c.solid, color: '#fff', ...style,
      }}>
        {isReactComponent(Icon) ? <Icon size={sz.icon} strokeWidth={2} /> : isValidElement(Icon) ? Icon : null}
        {children}
      </div>
    )
  }

  // ── Light: soft tinted circle ──────────────────
  return (
    <div style={{
      position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center',
      width: sz.mid, height: sz.mid, borderRadius: '50%', flexShrink: 0,
      background: c.light, color: c.text, ...style,
    }}>
      {isReactComponent(Icon) ? <Icon size={sz.icon} strokeWidth={2} /> : isValidElement(Icon) ? Icon : null}
      {children}
    </div>
  )
}
