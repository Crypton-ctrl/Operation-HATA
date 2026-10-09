import React, { createContext, useContext, useState, useEffect } from 'react'

export const THEMES = [
  {
    id: 'dark',
    name: 'Dark Mode',
    description: 'High-contrast dark mode for low-light environments.',
    accent: '#22d3ee',
    bg: '#05070d',
    badge: 'Default',
    icon: 'moon',
  },
  {
    id: 'light',
    name: 'Light Mode',
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
    let stored = localStorage.getItem('hata_theme')
    if (stored && ['netflix', 'cyber', 'matrix', 'midnight'].includes(stored)) {
      stored = 'dark'
    }
    return stored || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('hata_theme', theme)
  }, [theme])

  const setTheme = (newTheme) => {
    setThemeState(newTheme)
  }

  return (
    <ThemeContext.Provider value={{
      theme,
      setTheme,
      themes: THEMES,
      currentThemeMeta: THEMES.find(t => t.id === theme) || THEMES[0],
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
