import { useRef, useEffect, useId } from 'react'
import { animate, useMotionValue } from 'framer-motion'

function mapRange(value, fromLow, fromHigh, toLow, toHigh) {
  if (fromLow === fromHigh) return toLow
  const pct = (value - fromLow) / (fromHigh - fromLow)
  return toLow + pct * (toHigh - toLow)
}

/**
 * EtheralShadow — animated fluid shadow background.
 * Uses framer-motion + SVG feTurbulence displacement filters.
 */
export function EtheralShadow({
  sizing   = 'fill',
  color    = 'rgba(80, 70, 160, 1)',
  animation,
  noise,
  style,
  className = '',
}) {
  const rawId = useId()
  const id    = `shadowoverlay-${rawId.replace(/:/g, '')}`

  const animationEnabled    = animation && animation.scale > 0
  const feColorMatrixRef    = useRef(null)
  const hueRotateMotionValue = useMotionValue(180)
  const hueRotateAnimation   = useRef(null)

  const displacementScale = animation ? mapRange(animation.scale, 1, 100, 20, 100) : 0
  const animationDuration = animation ? mapRange(animation.speed, 1, 100, 1000, 50) : 1

  useEffect(() => {
    if (feColorMatrixRef.current && animationEnabled) {
      if (hueRotateAnimation.current) hueRotateAnimation.current.stop()
      hueRotateMotionValue.set(0)
      hueRotateAnimation.current = animate(hueRotateMotionValue, 360, {
        duration:    animationDuration / 25,
        repeat:      Infinity,
        repeatType:  'loop',
        repeatDelay: 0,
        ease:        'linear',
        delay:       0,
        onUpdate: (value) => {
          if (feColorMatrixRef.current) {
            feColorMatrixRef.current.setAttribute('values', String(value))
          }
        },
      })
      return () => { if (hueRotateAnimation.current) hueRotateAnimation.current.stop() }
    }
  }, [animationEnabled, animationDuration, hueRotateMotionValue])

  return (
    <div
      className={className}
      style={{ overflow: 'hidden', position: 'relative', width: '100%', height: '100%', ...style }}
    >
      <div style={{
        position: 'absolute',
        inset: -displacementScale,
        filter: animationEnabled ? `url(#${id}) blur(4px)` : 'none',
      }}>
        {animationEnabled && (
          <svg style={{ position: 'absolute', width: 0, height: 0 }}>
            <defs>
              <filter id={id}>
                <feTurbulence
                  result="undulation"
                  numOctaves="2"
                  baseFrequency={`${mapRange(animation.scale, 0, 100, 0.001, 0.0005)},${mapRange(animation.scale, 0, 100, 0.004, 0.002)}`}
                  seed="0"
                  type="turbulence"
                />
                <feColorMatrix
                  ref={feColorMatrixRef}
                  in="undulation"
                  type="hueRotate"
                  values="180"
                />
                <feColorMatrix
                  in="dist"
                  result="circulation"
                  type="matrix"
                  values="4 0 0 0 1  4 0 0 0 1  4 0 0 0 1  1 0 0 0 0"
                />
                <feDisplacementMap
                  in="SourceGraphic"
                  in2="circulation"
                  scale={displacementScale}
                  result="dist"
                />
                <feDisplacementMap
                  in="dist"
                  in2="undulation"
                  scale={displacementScale}
                  result="output"
                />
              </filter>
            </defs>
          </svg>
        )}
        <div style={{
          backgroundColor: color,
          maskImage:    `url('https://framerusercontent.com/images/ceBGguIpUU8luwByxuQz79t7To.png')`,
          maskSize:     sizing === 'stretch' ? '100% 100%' : 'cover',
          maskRepeat:   'no-repeat',
          maskPosition: 'center',
          WebkitMaskImage:    `url('https://framerusercontent.com/images/ceBGguIpUU8luwByxuQz79t7To.png')`,
          WebkitMaskSize:     sizing === 'stretch' ? '100% 100%' : 'cover',
          WebkitMaskRepeat:   'no-repeat',
          WebkitMaskPosition: 'center',
          width:  '100%',
          height: '100%',
        }} />
      </div>

      {noise && noise.opacity > 0 && (
        <div style={{
          position:   'absolute',
          inset:      0,
          backgroundImage: `url("https://framerusercontent.com/images/g0QcWrxr87K0ufOxIUFBakwYA8.png")`,
          backgroundSize:  `${noise.scale * 200}px`,
          backgroundRepeat: 'repeat',
          opacity:    noise.opacity / 2,
        }} />
      )}
    </div>
  )
}
