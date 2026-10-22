import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Lock, User, Shield, AlertCircle, Eye, EyeOff, UserPlus,
  LogIn, CheckCircle, Tv
} from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login({ onSuccess }) {
  const { login, register } = useAuth()
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

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search)
    const urlToken = searchParams.get('token')
    const urlError = searchParams.get('error')
    const urlDetail = searchParams.get('detail')

    if (urlToken) {
      sessionStorage.setItem('hata_token', urlToken)
      sessionStorage.removeItem('hata_user')
      window.location.href = '/' // Strip token from URL and let AuthContext fetch user
    }
    
    if (urlError) {
      const detailMsg = urlDetail ? `: ${decodeURIComponent(urlDetail)}` : ` (${urlError})`
      setError(`Google Auth Error${detailMsg}`)
    }
  }, [])

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

  const handleGoogleLogin = async () => {
    try {
      const backendUrl = import.meta.env.VITE_API_BASE_URL || '/api'
      const origin = encodeURIComponent(window.location.origin)
      // Fetch the Google OAuth URL as JSON from the backend, then redirect the browser
      // there ourselves. Letting window.location point at the proxy URL causes Vite to
      // swallow the 302 on the server side so the browser never reaches Google's page.
      const res = await fetch(`${backendUrl}/emails/oauth-login-url?redirect=${origin}`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        setError(err.detail || 'Failed to get Google login URL.')
        return
      }
      const { url } = await res.json()
      if (url) {
        window.location.href = url
      } else {
        setError('Server did not return a Google login URL.')
      }
    } catch (err) {
      setError('Could not connect to server for Google login.')
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

        {/* Google Auth Button */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          className="focus-ring w-full py-2.5 rounded-lg font-semibold text-sm bg-white text-gray-900 hover:bg-gray-100 transition-all shadow-sm flex items-center justify-center gap-2 mb-4 border border-gray-300"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          <span>{mode === 'login' ? 'Sign In with Google' : 'Register with Google'}</span>
        </button>

        <div className="flex items-center my-4">
          <div className="flex-1 border-t border-hata-border"></div>
          <span className="px-3 text-xs text-hata-muted">OR</span>
          <div className="flex-1 border-t border-hata-border"></div>
        </div>

        {/* Sign In Form */}
        {mode === 'login' ? (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-hata-muted font-medium">Username</label>
              <div className="relative mt-1.5">
                <User className="w-4 h-4 text-hata-muted absolute left-3 top-1/2 -translate-y-1/2" />
                <input
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
                <span>Authenticating.</span>
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
              <label className="text-xs text-hata-muted font-medium">Email</label>
              <input
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                placeholder="e.g. alex@hata.soc"
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
                <span>Creating Account.</span>
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
