import { useEffect, useRef } from 'react'

/**
 * NeuralBackground — Flow Field particle system
 * Adapted from TypeScript to plain JSX for this project.
 * No shadcn/cn dependency needed.
 */
export default function NeuralBackground({
  className = '',
  color = '#6366f1',
  trailOpacity = 0.12,
  particleCount = 500,
  speed = 1,
}) {
  const canvasRef     = useRef(null)
  const containerRef  = useRef(null)

  useEffect(() => {
    const canvas    = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let width  = container.clientWidth
    let height = container.clientHeight
    let particles = []
    let animationFrameId
    let mouse = { x: -1000, y: -1000 }

    const paintBackdrop = () => {
      ctx.fillStyle = document.documentElement.dataset.theme === 'light' ? '#05070D' : '#000000'
      ctx.fillRect(0, 0, width, height)
    }

    const createParticle = (initial = false) => {
      const particle = {
        x: Math.random() * width,
        y: Math.random() * height,
        vx: 0,
        vy: 0,
        age: initial ? Math.random() * 200 : 0,
        life: Math.random() * 200 + 100,
      }

      particle.reset = (firstRun = false) => {
        particle.x = Math.random() * width
        particle.y = Math.random() * height
        particle.vx = 0
        particle.vy = 0
        particle.age = firstRun ? Math.random() * 200 : 0
        particle.life = Math.random() * 200 + 100
      }

      particle.update = () => {
        const angle = (Math.cos(particle.x * 0.005) + Math.sin(particle.y * 0.005)) * Math.PI
        particle.vx += Math.cos(angle) * 0.2 * speed
        particle.vy += Math.sin(angle) * 0.2 * speed

        const dx = mouse.x - particle.x
        const dy = mouse.y - particle.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 150) {
          const force = (150 - dist) / 150
          particle.vx -= dx * force * 0.05
          particle.vy -= dy * force * 0.05
        }

        particle.x += particle.vx
        particle.y += particle.vy
        particle.vx *= 0.95
        particle.vy *= 0.95
        particle.age++

        if (particle.age > particle.life) particle.reset()

        if (particle.x < 0) particle.x = width
        if (particle.x > width) particle.x = 0
        if (particle.y < 0) particle.y = height
        if (particle.y > height) particle.y = 0
      }

      particle.draw = (ctx) => {
        const alpha = 1 - Math.abs((particle.age / particle.life) - 0.5) * 2
        ctx.globalAlpha = Math.max(0, alpha)
        ctx.fillStyle = color
        ctx.fillRect(particle.x, particle.y, 1.5, 1.5)
      }

      return particle
    }

    const init = () => {
      const dpr = window.devicePixelRatio || 1
      canvas.width  = width * dpr
      canvas.height = height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      canvas.style.width  = `${width}px`
      canvas.style.height = `${height}px`
      particles = Array.from({ length: particleCount }, () => createParticle(true))
      paintBackdrop()
    }

    const animate = () => {
      const lightMode = document.documentElement.dataset.theme === 'light'
      ctx.fillStyle = lightMode
        ? `rgba(5,7,13,${trailOpacity})`
        : `rgba(0,0,0,${trailOpacity})`
      ctx.fillRect(0, 0, width, height)
      particles.forEach((p) => { p.update(); p.draw(ctx) })
      animationFrameId = requestAnimationFrame(animate)
    }

    const onResize = () => {
      width  = container.clientWidth
      height = container.clientHeight
      init()
    }
    const onMouseMove = (e) => {
      const r = canvas.getBoundingClientRect()
      mouse.x = e.clientX - r.left
      mouse.y = e.clientY - r.top
    }
    const onMouseLeave = () => { mouse.x = -1000; mouse.y = -1000 }
    const onThemeChange = () => paintBackdrop()

    init()
    animate()
    window.addEventListener('resize', onResize)
    window.addEventListener('shieldguard-theme-change', onThemeChange)
    container.addEventListener('mousemove', onMouseMove)
    container.addEventListener('mouseleave', onMouseLeave)

    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('resize', onResize)
      window.removeEventListener('shieldguard-theme-change', onThemeChange)
      container.removeEventListener('mousemove', onMouseMove)
      container.removeEventListener('mouseleave', onMouseLeave)
    }
  }, [color, trailOpacity, particleCount, speed])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ position: 'absolute', inset: 0, background: 'var(--flow-bg, var(--bg))', overflow: 'hidden' }}
    >
      <canvas
        ref={canvasRef}
        style={{ display: 'block', width: '100%', height: '100%', filter: 'var(--flow-filter, none)' }}
      />
    </div>
  )
}
