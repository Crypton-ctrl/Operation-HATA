import React, { useEffect, useState } from 'react'
import {
  Save, Bot, SlidersHorizontal, Bell, KeyRound, Palette,
  Tv, Volume2, VolumeX, Check, User, Shield, Sparkles
} from 'lucide-react'
import { getSettings, updateSettings } from '../services/api.js'
import ErrorPanel from '../components/common/ErrorPanel.jsx'
import { useTheme } from '../context/ThemeContext.jsx'
import { useAuth } from '../context/AuthContext.jsx'

const MODULE_LABELS = {
  signature: 'File Signature Analysis', metadata: 'Metadata / EXIF Analysis',
  entropy: 'Entropy Analysis', steganography: 'Steganography Analysis',
  embedded: 'Embedded / Appended Data', yara: 'YARA Scanning',
  ocr: 'OCR Analysis', qr: 'QR Code Analysis', url: 'URL Analysis', ai: 'AI Interpretation',
}

export default function Settings() {
  const [settings, setSettings] = useState(null)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)

  const { theme, setTheme, themes, soundEnabled, toggleSound, triggerIntro } = useTheme()
  const { user, syncThemeWithProfile } = useAuth()

  const load = () => {
    setError(null)
    getSettings().then(setSettings).catch((e) => setError(e.message))
  }

  useEffect(() => { load() }, [])

  const save = async (partial) => {
    try {
      const updated = await updateSettings(partial)
      setSettings(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
    } catch (e) {
      setError(e.message)
    }
  }

  const handleSelectTheme = (tId) => {
    setTheme(tId)
    syncThemeWithProfile(tId)
  }

  if (error && !settings) return <ErrorPanel message={error} onRetry={load} />
  if (!settings) return <div className="text-hata-muted text-sm">Loading settings…</div>

  const toggleModule = (key) => {
    const modules = { ...settings.enabled_modules, [key]: !settings.enabled_modules[key] }
    save({ enabled_modules: modules })
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {saved && (
        <div className="rounded-lg border border-risk-safe/40 bg-risk-safe/10 text-risk-safe text-sm px-4 py-2">
          Settings saved.
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-risk-critical/40 bg-risk-critical/10 text-risk-critical text-sm px-4 py-2">
          {error}
        </div>
      )}

      {/* User Profile Card */}
      <section className="glass rounded-xl p-6 border border-hata-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-hata-accent" />
            <h3 className="font-semibold text-hata-text">Active Operator Profile</h3>
          </div>
          <span className="text-xs uppercase tracking-wider font-semibold px-2.5 py-1 rounded-full bg-hata-accent/15 text-hata-accent border border-hata-accent/30">
            {user?.role || 'Security Analyst'}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm bg-hata-panel/50 p-4 rounded-xl border border-hata-border/70">
          <div>
            <p className="text-xs text-hata-muted mb-0.5">Username</p>
            <p className="text-hata-text font-semibold font-mono">@{user?.username || 'operator'}</p>
          </div>
          <div>
            <p className="text-xs text-hata-muted mb-0.5">Full Name</p>
            <p className="text-hata-text font-medium">{user?.full_name || 'System Operator'}</p>
          </div>
          <div>
            <p className="text-xs text-hata-muted mb-0.5">Account ID</p>
            <p className="text-hata-text font-mono text-xs truncate">{user?.id || 'LOCAL-SESSION'}</p>
          </div>
        </div>
      </section>

      {/* Theme Management Section */}
      <section className="glass rounded-xl p-6 border border-hata-border">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Palette className="w-5 h-5 text-hata-accent" />
            <h3 className="font-semibold text-hata-text">Theme Management</h3>
          </div>
          <button
            onClick={triggerIntro}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600/20 text-red-400 border border-red-500/40 hover:bg-red-600 hover:text-white transition-all shadow-sm"
          >
            <Tv className="w-3.5 h-3.5" />
            <span>Play Netflix Pop</span>
          </button>
        </div>
        <p className="text-xs text-hata-muted mb-4">
          Personalize the SOC workstation display. Themes update color palettes, glowing borders, and visual hierarchy instantly.
        </p>

        {/* 5 Theme Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {themes.map((t) => {
            const isSelected = theme === t.id
            return (
              <div
                key={t.id}
                onClick={() => handleSelectTheme(t.id)}
                className={`p-4 rounded-xl border cursor-pointer transition-all relative flex flex-col justify-between ${
                  isSelected
                    ? 'border-hata-accent bg-hata-panel shadow-glow'
                    : 'border-hata-border bg-hata-panel/40 hover:bg-hata-panel hover:border-hata-border/90'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-4 h-4 rounded-full border border-white/30 shadow-sm shrink-0"
                        style={{ backgroundColor: t.accent }}
                      />
                      <span className="text-sm font-bold text-hata-text">{t.name}</span>
                    </div>
                    {isSelected ? (
                      <span className="flex items-center gap-1 text-[10px] font-semibold bg-hata-accent/20 text-hata-accent px-2 py-0.5 rounded-full">
                        <Check className="w-3 h-3" /> Active
                      </span>
                    ) : (
                      <span className="text-[10px] text-hata-muted bg-white/5 px-2 py-0.5 rounded-full">
                        {t.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-hata-muted line-clamp-2 leading-relaxed">
                    {t.description}
                  </p>
                </div>

                {/* Mini Swatch Bar */}
                <div className="mt-3 pt-2.5 border-t border-hata-border/60 flex items-center gap-1.5">
                  <div className="w-6 h-3 rounded" style={{ backgroundColor: t.bg, border: '1px solid #444' }} title="Background" />
                  <div className="w-6 h-3 rounded" style={{ backgroundColor: t.accent }} title="Accent" />
                  <div className="flex-1 text-[10px] text-right font-mono text-hata-muted">
                    {t.accent}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Cinematic Audio Options */}
        <div className="mt-5 pt-4 border-t border-hata-border/70 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {soundEnabled ? (
              <Volume2 className="w-4 h-4 text-hata-accent" />
            ) : (
              <VolumeX className="w-4 h-4 text-hata-muted" />
            )}
            <div>
              <p className="text-xs font-semibold text-hata-text">Netflix Intro "Ta-Dum" Audio</p>
              <p className="text-[11px] text-hata-muted">Play synthesized cinema chord during startup pop</p>
            </div>
          </div>
          <button
            onClick={toggleSound}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border ${
              soundEnabled
                ? 'bg-hata-accent/15 text-hata-accent border-hata-accent/40'
                : 'bg-white/5 text-hata-muted border-hata-border hover:text-hata-text'
            }`}
          >
            {soundEnabled ? 'Enabled' : 'Muted'}
          </button>
        </div>
      </section>

      {/* AI Configuration */}
      <section className="glass rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bot className="w-5 h-5 text-hata-accent" />
          <h3 className="font-semibold text-hata-text">AI Configuration</h3>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-hata-muted mb-1">Provider</p>
            <p className="text-hata-text font-medium">{settings.ai_provider}</p>
          </div>
          <div>
            <p className="text-xs text-hata-muted mb-1">Model</p>
            <p className="text-hata-text font-medium">{settings.ai_model}</p>
          </div>
          <div className="col-span-2 flex items-center gap-2 mt-2">
            <KeyRound className="w-4 h-4 text-hata-muted" />
            <p className="text-xs text-hata-muted">
              AI API Key: {settings.ai_api_key_configured
                ? <span className="text-risk-safe font-semibold">Configured</span>
                : <span className="text-risk-medium font-semibold">Not configured — technical fallback reports will be used</span>}
            </p>
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-hata-muted" />
            <p className="text-xs text-hata-muted">
              VirusTotal API Key: {settings.virustotal_api_key_configured
                ? <span className="text-risk-safe font-semibold">Configured</span>
                : <span className="text-hata-muted font-semibold">Not configured</span>}
            </p>
          </div>
        </div>
        <p className="text-[11px] text-hata-muted mt-4 italic">
          API keys are configured via server-side environment variables (.env) and are never exposed to the browser.
        </p>
      </section>

      {/* Scanner Configuration */}
      <section className="glass rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <SlidersHorizontal className="w-5 h-5 text-hata-accent" />
          <h3 className="font-semibold text-hata-text">Scanner Configuration</h3>
        </div>
        <div className="mb-4">
          <label className="text-xs text-hata-muted">Maximum upload size (MB)</label>
          <input
            type="number"
            defaultValue={settings.max_upload_mb}
            min={1}
            max={100}
            onBlur={(e) => save({ max_upload_mb: Number(e.target.value) })}
            className="focus-ring w-32 block mt-1 px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text"
          />
        </div>
        <div>
          <p className="text-xs text-hata-muted mb-2">Enabled Forensic Analysis Modules</p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(MODULE_LABELS).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm text-hata-text cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!settings.enabled_modules[key]}
                  onChange={() => toggleModule(key)}
                  className="accent-hata-accent w-4 h-4"
                />
                {label}
              </label>
            ))}
          </div>
        </div>
      </section>

      {/* Risk Thresholds */}
      <section className="glass rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <SlidersHorizontal className="w-5 h-5 text-hata-accent" />
          <h3 className="font-semibold text-hata-text">Risk Thresholds</h3>
        </div>
        <div className="grid grid-cols-5 gap-3 text-xs">
          {Object.entries(settings.risk_thresholds).map(([cat, val]) => (
            <div key={cat}>
              <p className="text-hata-muted mb-1">{cat}</p>
              <input
                type="number"
                defaultValue={val}
                min={0}
                max={100}
                onBlur={(e) => save({ risk_thresholds: { ...settings.risk_thresholds, [cat]: Number(e.target.value) } })}
                className="focus-ring w-full px-2 py-1.5 rounded-md bg-hata-panel2 border border-hata-border text-hata-text"
              />
            </div>
          ))}
        </div>
      </section>

      {/* Notifications */}
      <section className="glass rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-hata-accent" />
            <h3 className="font-semibold text-hata-text">Notifications</h3>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={settings.notifications_enabled}
              onChange={(e) => save({ notifications_enabled: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-hata-border rounded-full peer peer-checked:bg-hata-accent transition-colors relative">
              <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
            </div>
          </label>
        </div>
      </section>
    </div>
  )
}
