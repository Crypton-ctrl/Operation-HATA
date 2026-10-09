import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Lock, User, Shield, AlertCircle, Eye, EyeOff, UserPlus,
  LogIn, CheckCircle, Tv
} from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { useTheme } from '../context/ThemeContext.jsx'

export default function Login({ onSuccess }) {
  const { login, register } = useAuth()
  const { triggerIntro } = useTheme()

  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [showPassword, setShowPassword] = useState(false)

  // Login form state
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  // Register form state
  const [regFullName, setRegFullName] = useState('')
  const [regUsername, setRegUsername] = useState('')
  const [regEmail, setRegEmail] = useState('')
  const [regPassword, setRegPassword] = useState('')

  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [successMsg, setSuccessMsg] = useState(null)

  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(loginUsername, loginPassword)
      onSuccess?.()
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check credentials.')
    } finally {
      setBusy(false)
    }
  }

  const handleRegisterSubmit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await register({
        username: regUsername,
        password: regPassword,
        full_name: regFullName,
        email: regEmail,
      })
      setSuccessMsg('Account created! Authenticating session...')
      setTimeout(() => {
        onSuccess?.()
      }, 500)
    } catch (err) {
      setError(err.message || 'Registration failed.')
    } finally {
      setBusy(false)
    }
  }



  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden bg-hata-bg">
      {/* Background glow effects */}
      <div
        className="absolute inset-0 pointer-events-none opacity-40 transition-opacity duration-700"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 20%, rgba(var(--hata-glow), 0.2), transparent 45%), radial-gradient(circle at 80% 80%, rgba(var(--hata-glow), 0.15), transparent 45%)',
        }}
      />

      {/* Floating replay intro pop button in top right */}
      <div className="absolute top-6 right-6 z-20">
        <button
          onClick={triggerIntro}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-red-600/20 text-red-400 border border-red-500/40 hover:bg-red-600 hover:text-white transition-all shadow-[0_0_15px_rgba(229,9,20,0.3)] backdrop-blur-md"
        >
          <Tv className="w-3.5 h-3.5" />
          <span>Netflix Intro Pop</span>
        </button>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="relative w-full max-w-md glass rounded-2xl p-7 md:p-8 shadow-glow border border-hata-border/80"
      >
        {/* Header with animated logo */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-hata-accent to-hata-accent2 shadow-glow flex items-center justify-center mb-3">
            <Shield className="w-7 h-7 text-hata-bg" strokeWidth={2.5} />
          </div>
          <h1 className="text-xl font-extrabold tracking-wider text-hata-text">OPERATION HATA</h1>
          <p className="text-[11px] text-hata-muted mt-0.5 uppercase tracking-wider">
            Hidden Attachment Threat Analyzer
          </p>
        </div>

        {/* Tab switch between Sign In and Create Account */}
        <div className="flex p-1 bg-hata-panel rounded-xl border border-hata-border mb-6">
          <button
            type="button"
            onClick={() => { setMode('login'); setError(null) }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all ${
              mode === 'login'
                ? 'bg-hata-accent text-hata-bg shadow-sm'
                : 'text-hata-muted hover:text-hata-text'
            }`}
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>
          <button
            type="button"
            onClick={() => { setMode('register'); setError(null) }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all ${
              mode === 'register'
                ? 'bg-hata-accent text-hata-bg shadow-sm'
                : 'text-hata-muted hover:text-hata-text'
            }`}
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Create Account</span>
          </button>
        </div>

        {/* Error Alert */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-2 text-xs text-risk-critical bg-risk-critical/10 border border-risk-critical/30 rounded-lg px-3 py-2.5 mb-4"
            >
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </motion.div>
          )}

          {successMsg && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-2 text-xs text-risk-safe bg-risk-safe/10 border border-risk-safe/30 rounded-lg px-3 py-2.5 mb-4"
            >
              <CheckCircle className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Sign In Form */}
        {mode === 'login' ? (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-hata-muted font-medium">Username</label>
              <div className="relative mt-1.5">
                <User className="w-4 h-4 text-hata-muted absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  autoFocus
                  type="text"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  placeholder="Enter your username (e.g. admin)"
                  className="focus-ring w-full pl-9 pr-3 py-2.5 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text placeholder:text-hata-muted/50"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs text-hata-muted font-medium">Password</label>
              </div>
              <div className="relative mt-1.5">
                <Lock className="w-4 h-4 text-hata-muted absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="focus-ring w-full pl-9 pr-10 py-2.5 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text placeholder:text-hata-muted/50"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-hata-muted hover:text-hata-text"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={busy}
              className="focus-ring w-full py-2.5 rounded-lg font-semibold text-sm bg-hata-accent text-hata-bg hover:opacity-90 transition-all disabled:opacity-50 shadow-sm flex items-center justify-center gap-2 mt-2"
            >
              {busy ? (
                <span>Authenticating…</span>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>Sign In to Console</span>
                </>
              )}
            </button>


          </form>
        ) : (
          /* Create Account Form */
          <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
            <div>
              <label className="text-xs text-hata-muted font-medium">Full Name</label>
              <input
                autoFocus
                type="text"
                value={regFullName}
                onChange={(e) => setRegFullName(e.target.value)}
                placeholder="e.g. Alex Vance"
                className="focus-ring w-full px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text placeholder:text-hata-muted/50 mt-1"
                required
              />
            </div>

            <div>
              <label className="text-xs text-hata-muted font-medium">Username</label>
              <input
                type="text"
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                placeholder="e.g. alex_vance"
                className="focus-ring w-full px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text placeholder:text-hata-muted/50 mt-1"
                required
              />
            </div>



            <div>
              <label className="text-xs text-hata-muted font-medium">Password</label>
              <div className="relative mt-1">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="Minimum 6 characters"
                  className="focus-ring w-full pl-3 pr-10 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text placeholder:text-hata-muted/50"
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-hata-muted hover:text-hata-text"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={busy}
              className="focus-ring w-full py-2.5 rounded-lg font-semibold text-sm bg-hata-accent text-hata-bg hover:opacity-90 transition-all disabled:opacity-50 shadow-sm flex items-center justify-center gap-2 mt-4"
            >
              {busy ? (
                <span>Creating Account…</span>
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  <span>Register & Launch Console</span>
                </>
              )}
            </button>
          </form>
        )}

        <div className="mt-5 text-center">
          <p className="text-[11px] text-hata-muted">
            Operation HATA Enterprise Forensic Suite &bull; Individual Account Access
          </p>
        </div>
      </motion.div>
    </div>
  )
}
