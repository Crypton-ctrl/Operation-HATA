import { useEffect, useState, useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Mail, PlayCircle, StopCircle, RefreshCcw, CheckCircle2, XCircle, ShieldCheck, AlertCircle } from 'lucide-react'
import {
  getEmailStatus, getOAuthUrl, connectImap, disconnectEmail, startMonitoring, stopMonitoring, syncNow,
} from '../services/api.js'
import { useNotifications } from '../context/NotificationContext.jsx'
import ErrorPanel from '../components/common/ErrorPanel.jsx'

export default function AutomaticMonitoring() {
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [syncMsg, setSyncMsg] = useState(null)
  const [interval_, setInterval_] = useState(60)
  const [connectMethod, setConnectMethod] = useState('app_password') // 'app_password' | 'oauth'
  const [imapEmail, setImapEmail] = useState('')
  const [imapPassword, setImapPassword] = useState('')
  const { liveEvents } = useNotifications()
  const location = useLocation()
  const navigate = useNavigate()

  const load = useCallback(async () => {
    try { 
      const data = await getEmailStatus()
      setStatus(data)
      if (data?.poll_interval_seconds) {
        setInterval_(data.poll_interval_seconds)
      }
      setError(null) 
    } catch (e) { 
      setError(e.message) 
    }
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
      navigate('/automatic', { replace: true })
    } else if (connParam) {
      load()
      navigate('/automatic', { replace: true })
    }
  }, [location, navigate, load])

  const handleConnect = async (e) => {
    e?.preventDefault?.()
    setBusy(true); setError(null)
    try {
      const { url } = await getOAuthUrl(window.location.origin)
      window.location.href = url
    } catch (err) { 
      setError(err.message) 
      setBusy(false)
    }
  }

  const handleImapConnect = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await connectImap(imapEmail, imapPassword)
      await load()
    } catch (err) {
      setError(err.message || 'Failed to connect Gmail.')
    } finally {
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
    try { 
      await startMonitoring(interval_)
      await load() 
    } catch (e) { 
      setError(e.message) 
    }
    setBusy(false)
  }

  const handleStop = async () => {
    setBusy(true)
    await stopMonitoring().catch(() => {})
    await load()
    setBusy(false)
  }

  const handleSync = async () => {
    setBusy(true); setError(null); setSyncMsg(null)
    try { 
      const res = await syncNow()
      await load() 
      setSyncMsg(`Mailbox scan complete! Checked: ${res?.emails_checked ?? 0} emails, ${res?.attachments_analyzed ?? 0} attachments.`)
      setTimeout(() => setSyncMsg(null), 6000)
    } catch (e) { 
      setError(e.message) 
    }
    setBusy(false)
  }

  if (error && !status) return <ErrorPanel message={error} onRetry={load} />

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Mail className="w-5 h-5 text-hata-accent" />
          <h2 className="font-semibold text-hata-text">Gmail Threat Monitoring</h2>
          {status?.connected ? (
            <span className="ml-auto inline-flex items-center gap-1 text-xs text-risk-safe font-semibold bg-risk-safe/10 px-2.5 py-1 rounded-full border border-risk-safe/30">
              <CheckCircle2 className="w-3.5 h-3.5" /> Connected
            </span>
          ) : (
            <span className="ml-auto inline-flex items-center gap-1 text-xs text-hata-muted font-semibold bg-hata-panel2 px-2.5 py-1 rounded-full border border-hata-border">
              <XCircle className="w-3.5 h-3.5" /> Disconnected
            </span>
          )}
        </div>

        {!status?.connected ? (
          <div className="space-y-4">
            <div className="flex p-1 bg-hata-panel rounded-lg border border-hata-border mb-4">
              <button
                type="button"
                onClick={() => setConnectMethod('app_password')}
                className={`flex-1 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  connectMethod === 'app_password' ? 'bg-hata-accent text-hata-bg' : 'text-hata-muted hover:text-hata-text'
                }`}
              >
                Gmail App Password (Recommended)
              </button>
              <button
                type="button"
                onClick={() => setConnectMethod('oauth')}
                className={`flex-1 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  connectMethod === 'oauth' ? 'bg-hata-accent text-hata-bg' : 'text-hata-muted hover:text-hata-text'
                }`}
              >
                Google OAuth 2.0
              </button>
            </div>

            {connectMethod === 'app_password' ? (
              <form onSubmit={handleImapConnect} className="space-y-3">
                <p className="text-xs text-hata-muted">
                  Connect 24/7 background monitoring with a standard 16-character Google App Password. No Google approval or domain verification needed!
                </p>
                <div>
                  <label className="text-xs text-hata-muted font-medium">Your Gmail Address</label>
                  <input
                    type="email"
                    required
                    value={imapEmail}
                    onChange={(e) => setImapEmail(e.target.value)}
                    placeholder="e.g. user@gmail.com"
                    className="focus-ring w-full px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text placeholder:text-hata-muted/50 mt-1"
                  />
                </div>
                <div>
                  <div className="flex items-center justify-between">
                    <label className="text-xs text-hata-muted font-medium">Google App Password (16 letters)</label>
                    <a
                      href="https://myaccount.google.com/apppasswords"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-hata-accent hover:underline"
                    >
                      Generate App Password &rarr;
                    </a>
                  </div>
                  <input
                    type="password"
                    required
                    value={imapPassword}
                    onChange={(e) => setImapPassword(e.target.value)}
                    placeholder="xxxx xxxx xxxx xxxx"
                    className="focus-ring w-full px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text placeholder:text-hata-muted/50 mt-1 font-mono"
                  />
                </div>
                {error && <p className="text-xs text-risk-critical">{error}</p>}
                <button
                  type="submit"
                  disabled={busy}
                  className="focus-ring w-full py-2.5 rounded-lg font-semibold text-sm bg-hata-accent text-hata-bg hover:opacity-90 disabled:opacity-50 transition-colors shadow-sm"
                >
                  {busy ? 'Connecting...' : 'Connect & Start Monitoring'}
                </button>
              </form>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-hata-muted">
                  Connect your Gmail account using Google OAuth 2.0. Requires your email to be authorized on the Google Cloud Console.
                </p>
                {error && <p className="text-xs text-risk-critical">{error}</p>}
                <button
                  type="button"
                  disabled={busy}
                  onClick={handleConnect}
                  className="focus-ring w-full py-2.5 rounded-lg font-semibold text-sm bg-hata-accent text-hata-bg hover:opacity-90 disabled:opacity-50 transition-colors shadow-sm"
                >
                  {busy ? 'Connecting...' : 'Connect Gmail with OAuth'}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <p className="text-sm text-hata-text font-semibold">{status.email_address}</p>
                <p className="text-[11px] text-hata-muted">
                  {status.auth_method === 'imap_app_password' ? 'Connected via Gmail App Password (IMAP)' : 'Connected via Google OAuth 2.0'}
                </p>
              </div>
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                status.monitoring_active 
                  ? 'bg-risk-safe/15 text-risk-safe border border-risk-safe/40' 
                  : 'bg-hata-panel text-hata-muted border border-hata-border'
              }`}>
                <span className={`w-2 h-2 rounded-full ${status.monitoring_active ? 'bg-risk-safe animate-pulse' : 'bg-hata-muted'}`} />
                {status.monitoring_active ? 'MONITORING ACTIVE' : 'MONITORING PAUSED'}
              </span>
            </div>

            {status.auth_method === 'oauth2' && status.has_gmail_scope === false && (
              <div className="p-4 rounded-xl bg-risk-critical/10 border border-risk-critical/30 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-risk-critical text-xs">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>Gmail Read Permission Required</span>
                </div>
                <p className="text-xs text-hata-muted">
                  Google logged you in, but the <strong>"Read your email messages"</strong> permission checkbox was not checked during sign-in.
                </p>
                <div className="flex flex-wrap gap-2 pt-1">
                  <button 
                    type="button" 
                    onClick={handleConnect} 
                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-hata-accent text-hata-bg hover:opacity-90 shadow-sm"
                  >
                    Re-connect & Check Gmail Box
                  </button>
                  <button 
                    type="button" 
                    onClick={handleDisconnect} 
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-hata-panel2 border border-hata-border text-hata-text hover:bg-white/5"
                  >
                    Or Disconnect & Use App Password
                  </button>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-hata-muted bg-hata-panel/50 p-4 rounded-xl border border-hata-border/70">
              <div>
                <div className="text-[11px] text-hata-muted">Status</div>
                <div className={status.monitoring_active ? 'text-risk-safe font-bold' : 'text-hata-text font-bold'}>
                  {status.monitoring_active ? 'RUNNING' : 'STOPPED'}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-hata-muted">Emails Checked</div>
                <div className="text-hata-text font-semibold text-sm">{status.emails_checked}</div>
              </div>
              <div>
                <div className="text-[11px] text-hata-muted">Attachments Analyzed</div>
                <div className="text-hata-text font-semibold text-sm">{status.attachments_analyzed}</div>
              </div>
              <div>
                <div className="text-[11px] text-hata-muted">Last Checked</div>
                <div className="text-hata-text font-medium truncate">
                  {status.last_sync_at ? new Date(status.last_sync_at).toLocaleTimeString() : 'Never'}
                </div>
              </div>
            </div>

            {syncMsg && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-risk-safe/10 border border-risk-safe/30 text-risk-safe text-xs font-semibold">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{syncMsg}</span>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-risk-critical/10 border border-risk-critical/30 text-risk-critical text-xs">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex items-center gap-3 bg-hata-panel/30 p-3 rounded-lg border border-hata-border/40">
              <label className="text-xs text-hata-muted font-medium">Poll Interval (seconds)</label>
              <input 
                type="number" 
                min={15} 
                value={interval_} 
                onChange={(e) => setInterval_(Number(e.target.value))}
                className="focus-ring w-20 px-2.5 py-1 rounded-md bg-hata-panel2 border border-hata-border text-sm text-hata-text font-mono" 
              />
              <span className="text-[10px] text-hata-muted italic">How often HATA automatically checks for new attachments</span>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-hata-border/50">
              {!status.monitoring_active ? (
                <button 
                  disabled={busy} 
                  onClick={handleStart}
                  className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold bg-risk-safe/20 text-risk-safe border border-risk-safe/40 hover:bg-risk-safe/30 disabled:opacity-50 transition-colors shadow-sm"
                >
                  <PlayCircle className="w-4 h-4" /> Start Automatic Monitoring
                </button>
              ) : (
                <button 
                  disabled={busy} 
                  onClick={handleStop}
                  className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold bg-risk-critical/20 text-risk-critical border border-risk-critical/40 hover:bg-risk-critical/30 disabled:opacity-50 transition-colors shadow-sm"
                >
                  <StopCircle className="w-4 h-4" /> Pause Monitoring
                </button>
              )}
              <button 
                disabled={busy} 
                onClick={handleSync}
                className="focus-ring flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border border-hata-border text-hata-text hover:bg-white/5 disabled:opacity-50 transition-colors shadow-sm"
              >
                <RefreshCcw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} /> Scan Mailbox Now
              </button>
              <button 
                disabled={busy} 
                onClick={handleDisconnect}
                className="focus-ring ml-auto px-4 py-2 rounded-lg text-sm font-medium text-risk-critical hover:text-risk-critical/80 transition-colors border border-transparent hover:border-risk-critical/30"
              >
                Disconnect Mailbox
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="glass rounded-2xl p-6 text-xs text-hata-muted space-y-3">
        <div className="flex items-center gap-2 text-hata-text font-semibold text-sm">
          <ShieldCheck className="w-4 h-4 text-hata-accent" />
          <span>How Operation HATA Mailbox Protection Works</span>
        </div>
        <p>
          Once connected, Operation HATA runs continuous background surveillance on your mailbox. Incoming emails are scanned for image attachments (including steganographic images, polyglot files, hidden QR codes, and malicious payload containers).
        </p>
        <p>
          Detected image attachments are securely quarantined in memory/isolated storage and processed through the 12-layer forensic pipeline. Real-time threat alerts appear instantly on your dashboard when a suspicious attachment is detected.
        </p>
        <p className="italic text-[11px] border-l-2 border-hata-accent pl-2.5 mt-2 text-hata-muted/90">
          Emails are deduplicated using provider message IDs and SHA-256 hashes, ensuring zero duplicate overhead.
        </p>
      </div>
    </div>
  )
}
