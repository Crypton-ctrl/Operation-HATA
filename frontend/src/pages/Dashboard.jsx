import { useEffect, useState, useCallback } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { ScanSearch, ShieldAlert, ShieldCheck, ShieldX, Mail, RefreshCcw, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { getDashboardStats, seedDemoData } from '../services/api.js'
import { useNotifications } from '../context/NotificationContext.jsx'
import StatCard from '../components/dashboard/StatCard.jsx'
import RiskGauge from '../components/common/RiskGauge.jsx'
import ErrorPanel from '../components/common/ErrorPanel.jsx'
import { riskMeta } from '../utils/risk.js'

const COLORS = { SAFE: '#22c55e', LOW: '#38bdf8', MEDIUM: '#eab308', HIGH: '#f97316', CRITICAL: '#ef4444' }

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [seeding, setSeeding] = useState(false)
  const { liveEvents } = useNotifications()
  const navigate = useNavigate()

  const load = useCallback(async () => {
    try {
      const data = await getDashboardStats()
      setStats(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  // Refresh whenever a scan completes or dashboard_update fires
  useEffect(() => {
    const relevant = liveEvents.find(e => e.type === 'dashboard_update' || (e.type === 'scan_progress' && e.data.stage === 'complete'))
    if (relevant) load()
  }, [liveEvents, load])

  const handleSeedDemo = async () => {
    setSeeding(true)
    try { await seedDemoData() } catch (e) { setError(e.message) }
    await load()
    setSeeding(false)
  }

  if (loading) {
    return <div className="text-hata-muted text-sm">Loading dashboard…</div>
  }

  if (error && !stats) {
    return <ErrorPanel message={error} onRetry={load} />
  }

  const distribution = stats?.distribution || {}
  const pieData = Object.entries(distribution).map(([name, value]) => ({ name, value }))
  const hasAnyData = (stats?.total_scanned || 0) > 0

  return (
    <div className="space-y-6">
      {!hasAnyData && (
        <div className="glass rounded-xl p-5 flex items-center justify-between gap-4 border-hata-accent/30">
          <div className="flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-hata-accent shrink-0" />
            <div>
              <p className="text-sm font-semibold text-hata-text">No scan history yet</p>
              <p className="text-xs text-hata-muted">Load demo data to preview the dashboard, or head to Manual Scan to analyze a real image.</p>
            </div>
          </div>
          <button onClick={handleSeedDemo} disabled={seeding}
            className="focus-ring shrink-0 px-4 py-2 rounded-lg text-sm font-semibold bg-hata-accent text-hata-bg hover:bg-cyan-300 transition-colors disabled:opacity-50">
            {seeding ? 'Loading…' : 'Load Demo Data'}
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard icon={ScanSearch} label="Total Files Scanned" value={stats?.total_scanned ?? 0} tone="default" />
        <StatCard icon={ShieldX} label="Threats Detected" value={stats?.threats_detected ?? 0} tone="danger" hint="High + Critical" />
        <StatCard icon={ShieldAlert} label="Suspicious Files" value={stats?.suspicious_files ?? 0} tone="warn" hint="Medium risk" />
        <StatCard icon={ShieldCheck} label="Safe Files" value={stats?.safe_files ?? 0} tone="safe" hint="Safe + Low risk" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="glass rounded-xl p-6 flex flex-col items-center justify-center">
          <p className="text-xs uppercase tracking-wider text-hata-muted mb-4 font-semibold">Current Risk</p>
          <RiskGauge score={stats?.current_risk?.score ?? 0} category={stats?.current_risk?.category ?? 'SAFE'} size={180} />
        </div>

        <div className="glass rounded-xl p-5 lg:col-span-2">
          <p className="text-xs uppercase tracking-wider text-hata-muted mb-3 font-semibold">Threat Distribution</p>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={3}>
                  {pieData.map((entry) => <Cell key={entry.name} fill={COLORS[entry.name]} stroke="none" />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#0b0f19', border: '1px solid #1c2333', borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="glass rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs uppercase tracking-wider text-hata-muted font-semibold">Monitoring Status</p>
          <button onClick={() => navigate('/automatic')} className="text-xs text-hata-accent hover:underline focus-ring">Manage &rarr;</button>
        </div>
        <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
          <div className="flex items-center gap-2">
            <Mail className="w-4 h-4 text-hata-muted" />
            <span className="text-hata-muted">Connected email:</span>
            <span className={stats?.monitoring?.connected ? 'text-risk-safe font-semibold' : 'text-hata-muted'}>
              {stats?.monitoring?.connected ? stats.monitoring.email_address : 'Not connected'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <RefreshCcw className="w-4 h-4 text-hata-muted" />
            <span className="text-hata-muted">Monitoring:</span>
            <span className={stats?.monitoring?.monitoring_active ? 'text-risk-safe font-semibold' : 'text-hata-muted'}>
              {stats?.monitoring?.monitoring_active ? 'ACTIVE' : 'INACTIVE'}
            </span>
          </div>
          <div className="text-hata-muted">
            Emails checked: <span className="text-hata-text font-medium">{stats?.monitoring?.emails_checked ?? 0}</span>
          </div>
          <div className="text-hata-muted">
            Attachments analyzed: <span className="text-hata-text font-medium">{stats?.monitoring?.attachments_analyzed ?? 0}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <RecentTable title="Recent Attachments" rows={stats?.recent_attachments || []} navigate={navigate} />
        <RecentTable title="Recent Threats" rows={stats?.recent_threats || []} navigate={navigate} emptyText="No high-risk attachments detected." />
      </div>
    </div>
  )
}

function RecentTable({ title, rows, navigate, emptyText = 'No scans yet.' }) {
  return (
    <div className="glass rounded-xl p-5">
      <p className="text-xs uppercase tracking-wider text-hata-muted mb-3 font-semibold">{title}</p>
      {rows.length === 0 ? (
        <p className="text-xs text-hata-muted py-6 text-center">{emptyText}</p>
      ) : (
        <div className="space-y-1">
          {rows.map((r) => {
            const meta = riskMeta(r.risk_category)
            return (
              <button
                key={r.id}
                onClick={() => navigate(`/scan-result/${r.id}`)}
                className="focus-ring w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors text-left"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-hata-text truncate">{r.filename}</p>
                  <p className="text-[11px] text-hata-muted truncate">
                    {r.sender || (r.source === 'manual' ? 'Manual upload' : 'Unknown sender')} &middot; {new Date(r.started_at).toLocaleString()}
                  </p>
                </div>
                <span className={`shrink-0 text-xs font-bold px-2 py-1 rounded-md ${meta.bg}/10 ${meta.text}`}>
                  {r.risk_score}
                </span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
