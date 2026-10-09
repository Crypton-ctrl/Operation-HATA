import { useEffect, useState, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Mail, PlayCircle, StopCircle, RefreshCcw, CheckCircle2, XCircle } from 'lucide-react'
import {
  getEmailStatus, getOAuthUrl, disconnectEmail, startMonitoring, stopMonitoring, syncNow,
} from '../services/api.js'
import { useNotifications } from '../context/NotificationContext.jsx'
import ErrorPanel from '../components/common/ErrorPanel.jsx'

export default function AutomaticMonitoring() {
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [interval_, setInterval_] = useState(60)
  const { liveEvents } = useNotifications()
  const location = useLocation()
  const navigate = useNavigate()

  const load = useCallback(async () => {
    try { setStatus(await getEmailStatus()); setError(null) } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => { load() }, [load])
  
  useEffect(() => {
    if (liveEvents.some(e => e.type === 'scan_started' || e.type === 'dashboard_update')) load()
  }, [liveEvents, load])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const errParam = params.get('error')
    const connParam = params.get('connected')
    
    if (errParam) {
      setError(`Authentication failed: ${errParam}`)
      // clear param
      navigate('/automatic', { replace: true })
    } else if (connParam) {
      load()
      navigate('/automatic', { replace: true })
    }
  }, [location, navigate, load])

  const handleConnect = async (e) => {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      const { url } = await getOAuthUrl()
      window.location.href = url
    } catch (err) { 
      setError(err.message) 
      setBusy(false)
    }
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
          <div className="space-y-4">
            <p className="text-sm text-hata-muted">
              Connect your Gmail account securely using Google OAuth 2.0. HATA will never ask for or store your Gmail password. 
              We only request read-only access to scan incoming email attachments.
            </p>
            {error && <p className="text-xs text-risk-critical">{error}</p>}
            <button disabled={busy} onClick={handleConnect}
              className="focus-ring w-full py-2.5 rounded-lg font-semibold text-sm bg-hata-accent text-hata-bg hover:bg-cyan-300 disabled:opacity-50 transition-colors">
              Connect Gmail
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-hata-text font-medium">{status.email_address}</p>
            <div className="grid grid-cols-2 gap-4 text-xs text-hata-muted bg-hata-panel/50 p-4 rounded-xl border border-hata-border/70">
              <div>Last sync: <span className="text-hata-text font-semibold">{status.last_sync_at ? new Date(status.last_sync_at).toLocaleString() : 'Never'}</span></div>
              <div>Monitoring: <span className={status.monitoring_active ? 'text-risk-safe font-bold' : 'text-hata-text font-bold'}>{status.monitoring_active ? 'ACTIVE' : 'INACTIVE'}</span></div>
              <div>Emails checked: <span className="text-hata-text font-semibold">{status.emails_checked}</span></div>
              <div>Attachments analyzed: <span className="text-hata-text font-semibold">{status.attachments_analyzed}</span></div>
            </div>

            {error && <p className="text-xs text-risk-critical">{error}</p>}

            <div className="flex items-center gap-3 bg-hata-panel/30 p-3 rounded-lg border border-hata-border/40">
              <label className="text-xs text-hata-muted font-medium">Poll interval (sec)</label>
              <input type="number" min={15} value={interval_} onChange={(e) => setInterval_(Number(e.target.value))}
                className="focus-ring w-20 px-2 py-1 rounded-md bg-hata-panel2 border border-hata-border text-sm text-hata-text font-mono" />
              <span className="text-[10px] text-hata-muted italic">How often HATA checks for new mail</span>
            </div>

            <div className="flex flex-wrap gap-3 pt-2 border-t border-hata-border/50">
              {!status.monitoring_active ? (
                <button disabled={busy} onClick={handleStart}
                  className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold bg-risk-safe/20 text-risk-safe border border-risk-safe/40 hover:bg-risk-safe/30 disabled:opacity-50 transition-colors shadow-sm">
                  <PlayCircle className="w-4 h-4" /> Enable Automatic Scanning
                </button>
              ) : (
                <button disabled={busy} onClick={handleStop}
                  className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold bg-risk-critical/20 text-risk-critical border border-risk-critical/40 hover:bg-risk-critical/30 disabled:opacity-50 transition-colors shadow-sm">
                  <StopCircle className="w-4 h-4" /> Disable Automatic Scanning
                </button>
              )}
              <button disabled={busy} onClick={handleSync}
                className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border border-hata-border text-hata-text hover:bg-white/5 disabled:opacity-50 transition-colors shadow-sm">
                <RefreshCcw className="w-4 h-4" /> Manual Scan Mailbox
              </button>
              <button disabled={busy} onClick={handleDisconnect}
                className="focus-ring ml-auto px-4 py-2 rounded-lg text-sm font-medium text-risk-critical hover:text-risk-critical/80 transition-colors border border-transparent hover:border-risk-critical/30">
                Disconnect Gmail
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="glass rounded-2xl p-6 text-xs text-hata-muted space-y-3">
        <p className="font-semibold text-hata-text text-sm">How automatic monitoring works</p>
        <p>Once connected and explicitly started, HATA polls the inbox on the configured interval via the official Gmail API. It securely downloads any new image attachments into an isolated quarantine directory, and runs them through the multi-layer analysis pipeline.</p>
        <p>Emails and attachments are deduplicated using the provider Message-ID and file hash, so nothing is analyzed twice.</p>
        <p className="italic text-[10px] border-l-2 border-hata-accent pl-2 mt-2">
          Your Gmail account is connected via OAuth 2.0. HATA uses a restricted read-only scope ("https://www.googleapis.com/auth/gmail.readonly") and offline access to poll in the background. You can revoke access at any time.
        </p>
      </div>
    </div>
  )
}
