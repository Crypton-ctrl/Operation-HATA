import React, { useState, useRef, useEffect } from 'react'
import {
  Bell, Wifi, WifiOff, LogOut, Palette, Tv, User, Shield, ChevronDown, Check
} from 'lucide-react'
import { useNotifications } from '../../context/NotificationContext.jsx'
import { useAuth } from '../../context/AuthContext.jsx'
import { useTheme } from '../../context/ThemeContext.jsx'
import { riskMeta } from '../../utils/risk.js'
import { useNavigate } from 'react-router-dom'

const SEVERITY_TO_CATEGORY = { critical: 'CRITICAL', high: 'HIGH', medium: 'MEDIUM', low: 'LOW', info: 'SAFE' }

export default function TopNav({ title, subtitle, onLogout }) {
  const { notifications, unreadCount, markAllRead, socketConnected } = useNotifications()
  const { user } = useAuth()
  const { theme, setTheme, themes, currentThemeMeta } = useTheme()

  const [notifOpen, setNotifOpen] = useState(false)
  const [themeOpen, setThemeOpen] = useState(false)
  const [userOpen, setUserOpen] = useState(false)

  const notifRef = useRef(null)
  const themeRef = useRef(null)
  const userRef = useRef(null)

  const navigate = useNavigate()

  useEffect(() => {
    function handleClickOutside(event) {
      if (notifRef.current && !notifRef.current.contains(event.target)) setNotifOpen(false)
      if (themeRef.current && !themeRef.current.contains(event.target)) setThemeOpen(false)
      if (userRef.current && !userRef.current.contains(event.target)) setUserOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between gap-4 px-4 md:px-8 py-3.5 border-b border-hata-border bg-hata-bg/85 backdrop-blur-md">
      <div className="min-w-0">
        <h1 className="text-lg md:text-xl font-bold text-hata-text truncate">{title}</h1>
        {subtitle && <p className="text-xs text-hata-muted mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-2.5 shrink-0">

        {/* Theme Switcher Dropdown */}
        <div className="relative" ref={themeRef}>
          <button
            onClick={() => setThemeOpen(!themeOpen)}
            className="focus-ring flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-hata-border hover:bg-white/5 transition-colors text-xs font-medium text-hata-text"
            title="Change Theme"
          >
            <div
              className="w-3 h-3 rounded-full border border-white/20 shadow-sm"
              style={{ backgroundColor: currentThemeMeta.accent }}
            />
            <span className="hidden md:inline">{currentThemeMeta.name}</span>
            <ChevronDown className="w-3 h-3 text-hata-muted" />
          </button>

          {themeOpen && (
            <div className="absolute right-0 mt-2 w-56 glass rounded-xl shadow-2xl z-40 border border-hata-border py-1 overflow-hidden">
              <div className="px-3 py-2 border-b border-hata-border/70 text-[11px] font-semibold text-hata-muted uppercase tracking-wider flex items-center justify-between">
                <span>Theme Management</span>
                <Palette className="w-3 h-3" />
              </div>
              <div className="p-1 space-y-0.5">
                {themes.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => { setTheme(t.id); setThemeOpen(false) }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-colors ${
                      theme === t.id
                        ? 'bg-hata-accent/15 text-hata-accent font-semibold'
                        : 'text-hata-text hover:bg-white/5'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-3.5 h-3.5 rounded-full border border-white/30 shrink-0"
                        style={{ backgroundColor: t.accent }}
                      />
                      <span>{t.name}</span>
                    </div>
                    {theme === t.id && <Check className="w-3.5 h-3.5 text-hata-accent" />}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            className="focus-ring relative p-2 rounded-lg border border-hata-border hover:bg-white/5 transition-colors"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4 text-hata-text" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-risk-critical text-white text-[10px] flex items-center justify-center font-semibold">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto glass rounded-xl shadow-2xl z-40 border border-hata-border">
              <div className="flex items-center justify-between px-4 py-3 border-b border-hata-border">
                <span className="text-sm font-semibold text-hata-text">Notifications</span>
                <button onClick={markAllRead} className="text-xs text-hata-accent hover:underline focus-ring">
                  Mark all read
                </button>
              </div>
              {notifications.length === 0 ? (
                <div className="p-6 text-center text-xs text-hata-muted">No notifications yet.</div>
              ) : (
                notifications.slice(0, 15).map((n) => {
                  const cat = SEVERITY_TO_CATEGORY[n.severity] || 'SAFE'
                  const meta = riskMeta(cat)
                  return (
                    <button
                      key={n.id}
                      onClick={() => { setNotifOpen(false); if (n.scan_id) navigate(`/scan-result/${n.scan_id}`) }}
                      className={`w-full text-left px-4 py-3 border-b border-hata-border/60 hover:bg-white/5 transition-colors ${
                        n.read ? 'opacity-60' : ''
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${meta.bg}`} />
                        <span className="text-xs font-semibold text-hata-text">{n.title}</span>
                      </div>
                      <p className="text-[11px] text-hata-muted mt-1 line-clamp-2">{n.message}</p>
                    </button>
                  )
                })
              )}
            </div>
          )}
        </div>

        {/* User Profile Pill & Dropdown */}
        <div className="relative" ref={userRef}>
          <button
            onClick={() => setUserOpen(!userOpen)}
            className="focus-ring flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-hata-border hover:border-hata-accent/40 bg-hata-panel/50 hover:bg-white/5 transition-all text-xs"
          >
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-hata-accent to-hata-accent2 text-hata-bg font-bold flex items-center justify-center text-[11px] uppercase shadow-sm">
              {user?.username ? user.username.slice(0, 2) : 'OP'}
            </div>
            <div className="hidden sm:flex flex-col text-left">
              <span className="text-xs font-bold text-hata-text truncate max-w-[100px]">
                {user?.full_name || user?.username || 'Operator'}
              </span>
              <span className="text-[10px] text-hata-muted capitalize truncate max-w-[100px]">
                {user?.role || 'Analyst'}
              </span>
            </div>
            <ChevronDown className="w-3 h-3 text-hata-muted" />
          </button>

          {userOpen && (
            <div className="absolute right-0 mt-2 w-56 glass rounded-xl shadow-2xl z-40 border border-hata-border py-2 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-hata-border/70">
                <div className="text-xs font-bold text-hata-text">{user?.full_name || user?.username}</div>
                <div className="text-[11px] text-hata-muted">@{user?.username}</div>
                <span className="inline-block mt-1 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-hata-accent/15 text-hata-accent border border-hata-accent/30">
                  {user?.role || 'Security Analyst'}
                </span>
              </div>

              <div className="p-1">
                <button
                  onClick={() => { setUserOpen(false); navigate('/settings') }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-hata-text hover:bg-white/5 rounded-lg transition-colors text-left"
                >
                  <Shield className="w-3.5 h-3.5 text-hata-muted" />
                  <span>Security & Profile Settings</span>
                </button>

                <button
                  onClick={() => { setUserOpen(false); onLogout() }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-risk-critical hover:bg-risk-critical/10 rounded-lg transition-colors text-left font-medium"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
