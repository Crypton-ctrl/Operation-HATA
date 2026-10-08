import React, { createContext, useContext, useState, useEffect } from 'react'

export const THEMES = [
  {
    id: 'netflix',
    name: 'Netflix Crimson',
    description: 'Cinematic crimson red and deep pitch black with dramatic theater contrast.',
    accent: '#e50914',
    bg: '#0e0e0e',
    badge: 'Popular',
    icon: 'tv',
  },
  {
    id: 'cyber',
    name: 'Cyberpunk Cyan',
    description: 'Futuristic SOC neon cyan and obsidian blue with glowing holographic accents.',
    accent: '#22d3ee',
    bg: '#05070d',
    badge: 'Default',
    icon: 'shield',
  },
  {
    id: 'matrix',
    name: 'Matrix Green',
    description: 'Terminal hacker phosphor emerald with cybernetic data streams.',
    accent: '#22c55e',
    bg: '#040d08',
    badge: 'Hacker',
    icon: 'code',
  },
  {
    id: 'midnight',
    name: 'Midnight OLED',
    description: 'Electric violet aurora and cosmic deep black designed for night ops.',
    accent: '#a855f7',
    bg: '#05050f',
    badge: 'OLED',
    icon: 'moon',
  },
  {
    id: 'light',
    name: 'Analyst Light',
    description: 'High-contrast clean daylight theme optimized for daytime audit operations.',
    accent: '#0e7490',
    bg: '#f1f5f9',
    badge: 'Clean',
    icon: 'sun',
  },
]

const ThemeContext = createContext()

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    return localStorage.getItem('hata_theme') || 'netflix'
  })
  const [soundEnabled, setSoundEnabled] = useState(() => {
    return localStorage.getItem('hata_sound') !== 'false'
  })
  const [showIntro, setShowIntro] = useState(false)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('hata_theme', theme)
  }, [theme])

  const setTheme = (newTheme) => {
    setThemeState(newTheme)
  }

  const toggleSound = () => {
    setSoundEnabled(prev => {
      const next = !prev
      localStorage.setItem('hata_sound', String(next))
      return next
    })
  }

  const triggerIntro = () => {
    setShowIntro(true)
  }

  const closeIntro = () => {
    setShowIntro(false)
  }

  return (
    <ThemeContext.Provider value={{
      theme,
      setTheme,
      themes: THEMES,
      currentThemeMeta: THEMES.find(t => t.id === theme) || THEMES[0],
      soundEnabled,
      toggleSound,
      showIntro,
      triggerIntro,
      closeIntro,
    }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
