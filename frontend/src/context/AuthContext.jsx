import React, { createContext, useContext, useState, useEffect } from 'react'
import { login, logout, register, getMe, updateProfile } from '../services/api.js'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => sessionStorage.getItem('hata_token'))
  const [user, setUser] = useState(() => {
    try {
      const stored = sessionStorage.getItem('hata_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (token && !user) {
      getMe()
        .then(u => {
          setUser(u)
          sessionStorage.setItem('hata_user', JSON.stringify(u))
        })
        .catch(() => {
          // Token expired or invalid
          sessionStorage.removeItem('hata_token')
          sessionStorage.removeItem('hata_user')
          setToken(null)
          setUser(null)
        })
    }
  }, [token, user])

  useEffect(() => {
    const unauthorizedHandler = () => {
      sessionStorage.removeItem('hata_token')
      sessionStorage.removeItem('hata_user')
      setToken(null)
      setUser(null)
    }
    window.addEventListener('hata-unauthorized', unauthorizedHandler)
    return () => window.removeEventListener('hata-unauthorized', unauthorizedHandler)
  }, [])

  const mapLegacyTheme = (t) => {
    return ['netflix', 'cyber', 'matrix', 'midnight'].includes(t) ? 'dark' : t
  }

  const handleLogin = async (username, password) => {
    setLoading(true)
    try {
      const res = await login(username, password)
      sessionStorage.setItem('hata_token', res.token)
      setToken(res.token)
      if (res.user) {
        setUser(res.user)
        sessionStorage.setItem('hata_user', JSON.stringify(res.user))
        if (res.user.theme_preference) {
          const themeName = mapLegacyTheme(res.user.theme_preference)
          localStorage.setItem('hata_theme', themeName)
          document.documentElement.setAttribute('data-theme', themeName)
          window.dispatchEvent(new Event('hata-theme-changed'))
        }
      }
      return res
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (payload) => {
    setLoading(true)
    try {
      const res = await register(payload)
      sessionStorage.setItem('hata_token', res.token)
      setToken(res.token)
      if (res.user) {
        setUser(res.user)
        sessionStorage.setItem('hata_user', JSON.stringify(res.user))
        if (res.user.theme_preference) {
          const themeName = mapLegacyTheme(res.user.theme_preference)
          localStorage.setItem('hata_theme', themeName)
          document.documentElement.setAttribute('data-theme', themeName)
          window.dispatchEvent(new Event('hata-theme-changed'))
        }
      }
      return res
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    try {
      await logout()
    } catch {
      // ignore
    }
    sessionStorage.removeItem('hata_token')
    sessionStorage.removeItem('hata_user')
    setToken(null)
    setUser(null)
  }

  const syncThemeWithProfile = async (themeName) => {
    if (user && token) {
      try {
        const updated = await updateProfile({ theme_preference: themeName })
        setUser(updated)
        sessionStorage.setItem('hata_user', JSON.stringify(updated))
      } catch (err) {
        console.warn('Failed to update remote user theme:', err)
      }
    }
  }

  return (
    <AuthContext.Provider value={{
      user,
      token,
      isAuthenticated: Boolean(token),
      login: handleLogin,
      register: handleRegister,
      logout: handleLogout,
      syncThemeWithProfile,
      loading,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
