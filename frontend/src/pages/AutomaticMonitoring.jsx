import { useEffect, useState, useCallback } from 'react'
import { Mail, PlayCircle, StopCircle, RefreshCcw, CheckCircle2, XCircle } from 'lucide-react'
import {
  getEmailStatus, connectEmail, disconnectEmail, startMonitoring, stopMonitoring, syncNow,
} from '../services/api.js'
import { useNotifications } from '../context/NotificationContext.jsx'
import ErrorPanel from '../components/common/ErrorPanel.jsx'

export default function AutomaticMonitoring() {
  const [status, setStatus] = useState(null)
  const [form, setForm] = useState({ email_address: '', app_password: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [interval_, setInterval_] = useState(60)
  const { liveEvents } = useNotifications()

  const load = useCallback(async () => {
    try { setStatus(await getEmailStatus()); setError(null) } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (liveEvents.some(e => e.type === 'scan_started' || e.type === 'dashboard_update')) load()
  }, [liveEvents, load])

  const handleConnect = async (e) => {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      await connectEmail(form)
      setForm({ email_address: '', app_password: '' })
      await load()
    } catch (err) { setError(err.message) }
    setBusy(false)
  }

  const handleDisconnect = async () => {
    setBusy(true)
    await disconnectEmail().catch((e) => setError(e.message))
    await load()
    setBusy(false)
  }

  const handleStart = async () => {
    setBusy(true); setError(null)
    try { await startMonitoring(interval_); await load() } catch (e) { setError(e.message) }
    setBusy(false)
  }

  const handleStop = async () => {
    setBusy(true)
    await stopMonitoring().catch(() => {})
    await load()
    setBusy(false)
  }

  const handleSync = async () => {
    setBusy(true); setError(null)
    try { await syncNow(); await load() } catch (e) { setError(e.message) }
    setBusy(false)
  }

  if (error && !status) return <ErrorPanel message={error} onRetry={load} />

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Mail className="w-5 h-5 text-hata-accent" />
          <h2 className="font-semibold text-hata-text">Gmail Connection</h2>
          {status?.connected ? (
            <span className="ml-auto inline-flex items-center gap-1 text-xs text-risk-safe font-semibold">
              <CheckCircle2 className="w-4 h-4" /> Connected
            </span>
          ) : (
            <span className="ml-auto inline-flex items-center gap-1 text-xs text-hata-muted font-semibold">
              <XCircle className="w-4 h-4" /> Disconnected
            </span>
          )}
        </div>

        {!status?.connected ? (
          <form onSubmit={handleConnect} className="space-y-3">
            <p className="text-xs text-hata-muted">
              Connects via secure IMAP using a Gmail <strong>App Password</strong> (requires 2FA enabled on the
              Google account). Your regular password is never used or requested, and the credential is encrypted
              before storage. Generate one at myaccount.google.com &rarr; Security &rarr; App Passwords.
            </p>
            <div>
              <label className="text-xs text-hata-muted">Gmail address</label>
              <input required type="email" value={form.email_address}
                onChange={(e) => setForm({ ...form, email_address: e.target.value })}
                className="focus-ring w-full mt-1 px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text"
                placeholder="you@gmail.com" />
            </div>
            <div>
              <label className="text-xs text-hata-muted">App Password</label>
              <input required type="password" value={form.app_password}
                onChange={(e) => setForm({ ...form, app_password: e.target.value })}
                className="focus-ring w-full mt-1 px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text"
                placeholder="xxxx xxxx xxxx xxxx" />
            </div>
            {error && <p className="text-xs text-risk-critical">{error}</p>}
            <button disabled={busy} type="submit"
              className="focus-ring w-full py-2.5 rounded-lg font-semibold text-sm bg-hata-accent text-hata-bg hover:bg-cyan-300 disabled:opacity-50">
              Connect Gmail
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-hata-text">{status.email_address}</p>
            <div className="grid grid-cols-2 gap-4 text-xs text-hata-muted">
              <div>Last sync: <span className="text-hata-text">{status.last_sync_at ? new Date(status.last_sync_at).toLocaleString() : 'Never'}</span></div>
              <div>Monitoring: <span className={status.monitoring_active ? 'text-risk-safe font-semibold' : 'text-hata-text'}>{status.monitoring_active ? 'ACTIVE' : 'INACTIVE'}</span></div>
              <div>Emails checked: <span className="text-hata-text">{status.emails_checked}</span></div>
              <div>Attachments analyzed: <span className="text-hata-text">{status.attachments_analyzed}</span></div>
            </div>

            {error && <p className="text-xs text-risk-critical">{error}</p>}

            <div className="flex items-center gap-2">
              <label className="text-xs text-hata-muted">Poll interval (sec)</label>
              <input type="number" min={15} value={interval_} onChange={(e) => setInterval_(Number(e.target.value))}
                className="focus-ring w-20 px-2 py-1 rounded-md bg-hata-panel2 border border-hata-border text-sm text-hata-text" />
            </div>

            <div className="flex flex-wrap gap-2">
              {!status.monitoring_active ? (
                <button disabled={busy} onClick={handleStart}
                  className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-risk-safe/20 text-risk-safe border border-risk-safe/40 hover:bg-risk-safe/30 disabled:opacity-50">
                  <PlayCircle className="w-4 h-4" /> START MONITORING
                </button>
              ) : (
                <button disabled={busy} onClick={handleStop}
                  className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-risk-critical/20 text-risk-critical border border-risk-critical/40 hover:bg-risk-critical/30 disabled:opacity-50">
                  <StopCircle className="w-4 h-4" /> STOP MONITORING
                </button>
              )}
              <button disabled={busy} onClick={handleSync}
                className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border border-hata-border text-hata-text hover:bg-white/5 disabled:opacity-50">
                <RefreshCcw className="w-4 h-4" /> SYNC NOW
              </button>
              <button disabled={busy} onClick={handleDisconnect}
                className="focus-ring ml-auto px-4 py-2 rounded-lg text-sm font-medium text-hata-muted hover:text-hata-text">
                Disconnect
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="glass rounded-2xl p-6 text-xs text-hata-muted space-y-2">
        <p className="font-semibold text-hata-text text-sm">How automatic monitoring works</p>
        <p>Once connected and started, HATA polls the inbox on the configured interval, downloads any new
           image attachments into an isolated quarantine directory, and runs them through the exact same
           multi-layer analysis pipeline used by Manual Scan. Emails and attachments are deduplicated using
           the provider Message-ID and file hash, so nothing is analyzed twice.</p>
      </div>
    </div>
  )
}
