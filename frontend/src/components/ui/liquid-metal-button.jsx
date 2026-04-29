import { motion } from 'framer-motion'
import { Loader } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs) {
  return twMerge(clsx(inputs))
}

const HEIGHT = 48
const MIN_WIDTH = 142

const movingMap = {
  TOP: 'radial-gradient(20.7% 50% at 50% 0%, hsl(0, 0%, 100%) 0%, rgba(255, 255, 255, 0) 100%)',
  LEFT: 'radial-gradient(16.6% 43.1% at 0% 50%, hsl(0, 0%, 100%) 0%, rgba(255, 255, 255, 0) 100%)',
  BOTTOM: 'radial-gradient(20.7% 50% at 50% 100%, hsl(0, 0%, 100%) 0%, rgba(255, 255, 255, 0) 100%)',
  RIGHT: 'radial-gradient(16.2% 41.2% at 100% 50%, hsl(0, 0%, 100%) 0%, rgba(255, 255, 255, 0) 100%)',
}

const highlight =
  'radial-gradient(75% 181.15942028985506% at 50% 50%, #3275F8 0%, rgba(255, 255, 255, 0) 100%)'

function HoverBorderGradient({
  children,
  containerClassName,
  className,
  as: Element = 'button',
  duration = 1,
  clockwise = true,
  disabled = false,
  ...props
}) {
  const [hovered, setHovered] = useState(false)
  const [direction, setDirection] = useState('BOTTOM')

  useEffect(() => {
    if (hovered || disabled) return

    const directions = ['TOP', 'LEFT', 'BOTTOM', 'RIGHT']
    const interval = setInterval(() => {
      setDirection((currentDirection) => {
        const currentIndex = directions.indexOf(currentDirection)
        const nextIndex = clockwise
          ? (currentIndex - 1 + directions.length) % directions.length
          : (currentIndex + 1) % directions.length
        return directions[nextIndex]
      })
    }, duration * 1000)

    return () => clearInterval(interval)
  }, [clockwise, disabled, duration, hovered])

  return (
    <Element
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      disabled={disabled}
      className={cn(
        'relative flex h-min w-fit flex-col flex-nowrap content-center items-center justify-center gap-10 overflow-visible rounded-full border border-white/10 bg-black/40 box-decoration-clone p-px backdrop-blur-sm transition duration-500 hover:bg-black/60 disabled:cursor-not-allowed disabled:opacity-45',
        containerClassName,
      )}
      {...props}
    >
      <div
        className={cn(
          'z-10 w-auto rounded-[inherit] bg-black px-4 py-2 text-white',
          className,
        )}
      >
        {children}
      </div>
      <motion.div
        className="absolute inset-0 z-0 flex-none overflow-hidden rounded-[inherit]"
        style={{
          filter: 'blur(2px)',
          position: 'absolute',
          width: '100%',
          height: '100%',
        }}
        initial={{ background: movingMap[direction] }}
        animate={{
          background: hovered && !disabled
            ? [movingMap[direction], highlight]
            : movingMap[direction],
        }}
        transition={{ ease: 'linear', duration }}
      />
      <div className="absolute inset-0.5 z-[1] flex-none rounded-[100px] bg-black" />
    </Element>
  )
}

export function LiquidMetalButton({
  label = 'Get Started',
  onClick,
  viewMode = 'text',
  fullWidth = false,
  disabled = false,
  loading = false,
}) {
  const [width, setWidth] = useState(MIN_WIDTH)
  const wrapRef = useRef(null)

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

  const buttonWidth = viewMode === 'icon' ? HEIGHT : fullWidth ? width : MIN_WIDTH

  return (
    <div
      ref={wrapRef}
      style={{
        display: fullWidth ? 'block' : 'inline-block',
        width: fullWidth ? '100%' : 'auto',
      }}
    >
      <HoverBorderGradient
        onClick={onClick}
        disabled={disabled || loading}
        aria-label={label}
        containerClassName="w-full"
        className="flex h-[46px] items-center justify-center rounded-full px-6 font-['Plus_Jakarta_Sans'] text-sm font-semibold tracking-[0.4px] text-slate-100"
        style={{ width: buttonWidth }}
      >
        {loading && (
          <Loader
            size={16}
            className="mr-2 inline-block animate-spin align-[-2px] text-slate-300"
          />
        )}
        {viewMode === 'icon' ? null : label}
      </HoverBorderGradient>
    </div>
  )
}
