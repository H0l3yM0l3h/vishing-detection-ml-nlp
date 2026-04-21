import { liquidMetalFragmentShader, ShaderMount } from '@paper-design/shaders'
import { Sparkles, Loader } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

/**
 * LiquidMetalButton — adapted from paper-design/shaders reference.
 * Additions vs original:
 *   - fullWidth: resizes to match parent container via ResizeObserver
 *   - disabled: grays out and blocks interaction
 *   - loading: shows spinning Loader icon
 */

const HEIGHT    = 46
const MIN_WIDTH = 142

export function LiquidMetalButton({
  label     = 'Get Started',
  onClick,
  viewMode  = 'text',
  fullWidth = false,
  disabled  = false,
  loading   = false,
}) {
  const [isHovered, setIsHovered] = useState(false)
  const [isPressed, setIsPressed] = useState(false)
  const [ripples,   setRipples]   = useState([])
  const [width,     setWidth]     = useState(MIN_WIDTH)

  const wrapRef     = useRef(null)
  const shaderRef   = useRef(null)
  const shaderMount = useRef(null)
  const buttonRef   = useRef(null)
  const rippleId    = useRef(0)

  /* ── Measure parent width for fullWidth mode ── */
  useEffect(() => {
    if (!fullWidth || !wrapRef.current) return
    const parent = wrapRef.current.parentElement
    if (!parent) return
    const update = () => setWidth(parent.offsetWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(parent)
    return () => ro.disconnect()
  }, [fullWidth])

  /* ── Inject global styles once ── */
  useEffect(() => {
    const styleId = 'liquid-metal-style'
    if (!document.getElementById(styleId)) {
      const s = document.createElement('style')
      s.id = styleId
      s.textContent = `
        .lm-shader canvas {
          width: 100% !important; height: 100% !important;
          display: block !important; position: absolute !important;
          top: 0 !important; left: 0 !important;
          border-radius: 100px !important;
        }
        @keyframes lm-ripple {
          0%   { transform: translate(-50%,-50%) scale(0); opacity:.6 }
          100% { transform: translate(-50%,-50%) scale(4); opacity:0  }
        }
        @keyframes lm-spin {
          to { transform: rotate(360deg); }
        }
      `
      document.head.appendChild(s)
    }
  }, [])

  /* ── Re-mount shader whenever the button width changes ── */
  const btnW = viewMode === 'icon' ? 46 : fullWidth ? width : MIN_WIDTH
  const innerW = btnW - 4

  useEffect(() => {
    if (!shaderRef.current || btnW === 0) return
    shaderMount.current?.destroy?.()
    shaderMount.current = null

    shaderMount.current = new ShaderMount(
      shaderRef.current,
      liquidMetalFragmentShader,
      { u_repetition: 4, u_softness: .5, u_shiftRed: .3, u_shiftBlue: .3,
        u_distortion: 0, u_contour: 0, u_angle: 45, u_scale: 8, u_shape: 1,
        u_offsetX: .1, u_offsetY: -.1 },
      { width: btnW, height: HEIGHT },
      0.6,
    )

    return () => { shaderMount.current?.destroy?.(); shaderMount.current = null }
  }, [btnW])


  const handleEnter = () => {
    if (disabled) return
    setIsHovered(true)
    shaderMount.current?.setSpeed?.(1)
  }
  const handleLeave = () => {
    setIsHovered(false); setIsPressed(false)
    shaderMount.current?.setSpeed?.(0.6)
  }
  const handleClick = (e) => {
    if (disabled || loading) return
    shaderMount.current?.setSpeed?.(2.4)
    setTimeout(() => shaderMount.current?.setSpeed?.(isHovered ? 1 : 0.6), 300)
    const rect = buttonRef.current.getBoundingClientRect()
    const ripple = { x: e.clientX - rect.left, y: e.clientY - rect.top, id: rippleId.current++ }
    setRipples(p => [...p, ripple])
    setTimeout(() => setRipples(p => p.filter(r => r.id !== ripple.id)), 600)
    onClick?.()
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative', display: fullWidth ? 'block' : 'inline-block' }}>
      <div style={{ perspective: '1000px', perspectiveOrigin: '50% 50%' }}>
        <div style={{
          position: 'relative', width: btnW, height: HEIGHT,
          transformStyle: 'preserve-3d', transition: 'all .8s cubic-bezier(.34,1.56,.64,1)',
          opacity: disabled ? 0.4 : 1,
        }}>

          {/* Label layer */}
          <div style={{
            position: 'absolute', top: 0, left: 0, width: btnW, height: HEIGHT,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            transform: 'translateZ(20px)', zIndex: 30, pointerEvents: 'none',
          }}>
            {loading ? (
              <Loader size={16} style={{ color: '#888', animation: 'lm-spin 1s linear infinite' }} />
            ) : viewMode === 'icon' ? (
              <Sparkles size={16} style={{ color: '#666', filter: 'drop-shadow(0 1px 2px rgba(0,0,0,.5))' }} />
            ) : (
              <span style={{
                fontSize: 14, color: '#777', fontWeight: 500,
                textShadow: '0 1px 2px rgba(0,0,0,.5)', whiteSpace: 'nowrap',
                fontFamily: "'Plus Jakarta Sans', sans-serif", letterSpacing: '.5px',
              }}>
                {loading ? 'Analyzing...' : label}
              </span>
            )}
          </div>

          {/* Inner dark fill */}
          <div style={{
            position: 'absolute', top: 0, left: 0, width: btnW, height: HEIGHT,
            transform: `translateZ(10px) ${isPressed ? 'translateY(1px) scale(.98)' : 'none'}`,
            zIndex: 20, transition: 'transform .15s ease',
          }}>
            <div style={{
              width: innerW, height: HEIGHT - 4, margin: 2, borderRadius: 100,
              background: 'linear-gradient(180deg,#202020 0%,#000 100%)',
              boxShadow: isPressed ? 'inset 0 2px 4px rgba(0,0,0,.4)' : 'none',
              transition: 'box-shadow .15s ease',
            }} />
          </div>

          {/* Shader / outer ring layer */}
          <div style={{
            position: 'absolute', top: 0, left: 0, width: btnW, height: HEIGHT,
            transform: `translateZ(0) ${isPressed ? 'translateY(1px) scale(.98)' : 'none'}`,
            zIndex: 10, transition: 'transform .15s ease',
          }}>
            <div style={{
              width: btnW, height: HEIGHT, borderRadius: 100,
              boxShadow: isPressed
                ? '0 0 0 1px rgba(0,0,0,.5),0 1px 2px rgba(0,0,0,.3)'
                : isHovered
                  ? '0 0 0 1px rgba(0,0,0,.4),0 12px 6px rgba(0,0,0,.05),0 8px 5px rgba(0,0,0,.1),0 4px 4px rgba(0,0,0,.15),0 1px 2px rgba(0,0,0,.2)'
                  : '0 0 0 1px rgba(0,0,0,.3),0 9px 9px rgba(0,0,0,.12),0 2px 5px rgba(0,0,0,.15)',
              transition: 'box-shadow .15s ease',
              background: 'transparent',
            }}>
              <div
                ref={shaderRef}
                className="lm-shader"
                style={{
                  borderRadius: 100, overflow: 'hidden',
                  position: 'relative', width: btnW, height: HEIGHT,
                }}
              />
            </div>
          </div>

          {/* Transparent click target */}
          <button
            ref={buttonRef}
            onClick={handleClick}
            onMouseEnter={handleEnter}
            onMouseLeave={handleLeave}
            onMouseDown={() => !disabled && setIsPressed(true)}
            onMouseUp={() => setIsPressed(false)}
            disabled={disabled || loading}
            aria-label={label}
            style={{
              position: 'absolute', top: 0, left: 0, width: btnW, height: HEIGHT,
              background: 'transparent', border: 'none',
              cursor: disabled || loading ? 'not-allowed' : 'pointer',
              outline: 'none', zIndex: 40,
              transform: 'translateZ(25px)', borderRadius: 100, overflow: 'hidden',
            }}
          >
            {ripples.map(r => (
              <span key={r.id} style={{
                position: 'absolute', left: r.x, top: r.y,
                width: 20, height: 20, borderRadius: '50%',
                background: 'radial-gradient(circle,rgba(255,255,255,.4) 0%,transparent 70%)',
                pointerEvents: 'none', animation: 'lm-ripple .6s ease-out',
              }} />
            ))}
          </button>
        </div>
      </div>
    </div>
  )
}
