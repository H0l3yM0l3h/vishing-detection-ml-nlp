import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useAuthStore } from '../hooks/useAuth'
import LoginForm from '../components/auth/LoginForm'
import RegisterForm from '../components/auth/RegisterForm'
import { TunnelBackground } from '../components/ui/tunnel-background'

export default function LoginPage() {
  const [mode, setMode] = useState('login')
  const token = useAuthStore((s) => s.token)
  const navigate = useNavigate()

  useEffect(() => {
    if (token) navigate('/app', { replace: true })
  }, [token, navigate])

  const titleWords = "SHIELD GUARD".split(" ");

  return (
    <TunnelBackground>
      <div className="w-full max-w-md mx-auto relative z-20 flex flex-col items-center">
        
        {/* Startup Wow Title */}
        <div className="text-center mb-8">
          <h1 className="font-display text-5xl sm:text-6xl font-black mb-2 tracking-tighter flex justify-center flex-wrap gap-4">
            {titleWords.map((word, wordIndex) => (
                <span
                    key={wordIndex}
                    className="inline-block"
                >
                    {word.split("").map((letter, letterIndex) => (
                        <motion.span
                            key={`${wordIndex}-${letterIndex}`}
                            initial={{ y: 50, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            transition={{
                                delay: wordIndex * 0.1 + letterIndex * 0.03,
                                type: "spring",
                                stiffness: 150,
                                damping: 25,
                            }}
                            className={`inline-block text-transparent bg-clip-text bg-gradient-to-br 
                              ${wordIndex === 0 ? "from-white to-blue-200" : "from-red-400 to-red-600"}`}
                        >
                            {letter}
                        </motion.span>
                    ))}
                </span>
            ))}
          </h1>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.8 }}
            className="font-mono text-[10px] sm:text-xs text-[var(--blue)] tracking-[4px] uppercase mt-2"
          >
            Vishing Detection System
          </motion.div>
        </div>

        {/* Card */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1, duration: 0.6, ease: "easeOut" }}
          className="w-full"
        >
          <div className="sg-card sg-card-glow !p-8 backdrop-blur-xl bg-[var(--c1)]/80 shadow-2xl border-white/5">
            {mode === 'login' ? (
              <LoginForm onSwitchToRegister={() => setMode('register')} />
            ) : (
              <RegisterForm onSwitchToLogin={() => setMode('login')} />
            )}
          </div>
        </motion.div>

        {/* Footer */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5, duration: 1 }}
          className="text-center mt-8"
        >
          <div className="font-mono text-[9px] text-[var(--muted)] tracking-[3px]">
            SHIELDGUARD v2.0 — HYBRID INTELLIGENCE
          </div>
        </motion.div>
      </div>
    </TunnelBackground>
  )
}
