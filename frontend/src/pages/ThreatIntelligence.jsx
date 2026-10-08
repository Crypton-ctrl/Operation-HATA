import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid } from 'recharts'
import { ShieldAlert, Hash, Users, ScanLine } from 'lucide-react'
import { getThreatIntel } from '../services/api.js'
import StatCard from '../components/dashboard/StatCard.jsx'
import ErrorPanel from '../components/common/ErrorPanel.jsx'

export default function ThreatIntelligence() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true); setError(null)
    getThreatIntel().then((d) => { setData(d); setLoading(false) })
      .catch((e) => { setError(e.message); setLoading(false) })
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="text-hata-muted text-sm">Loading threat intelligence…</div>
  if (error) return <ErrorPanel message={error} onRetry={load} />
  if (!data) return null

  const findingsChart = data.top_findings.map(f => ({ name: f.finding.slice(0, 28), count: f.count }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard icon={ShieldAlert} label="Total Threats Detected" value={data.total_threats_detected} tone="danger" />
        <StatCard icon={Hash} label="Repeated File Hashes" value={data.repeated_hashes.length} tone="warn" />
        <StatCard icon={Users} label="Repeated Senders" value={data.repeated_senders.length} tone="warn" />
      </div>

      {!data.virustotal_configured && (
        <div className="text-xs text-hata-muted glass rounded-lg px-4 py-3">
          External reputation service (VirusTotal) is not configured — this dashboard uses local scan history only.
        </div>
      )}

      <div className="glass rounded-xl p-5">
        <p className="text-xs uppercase tracking-wider text-hata-muted font-semibold mb-3">Top Contributing Findings</p>
        {findingsChart.length === 0 ? (
          <p className="text-xs text-hata-muted py-8 text-center">No findings recorded yet.</p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={findingsChart} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c2333" horizontal={false} />
                <XAxis type="number" stroke="#7c8aa5" fontSize={11} />
                <YAxis type="category" dataKey="name" stroke="#7c8aa5" fontSize={10} width={180} />
                <Tooltip contentStyle={{ background: '#0b0f19', border: '1px solid #1c2333', fontSize: 12 }} />
                <Bar dataKey="count" fill="#22d3ee" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <ListPanel icon={ScanLine} title="Top YARA Rule Matches" rows={data.top_yara_rules.map(r => ({ label: r.rule, count: r.count }))} />
        <ListPanel icon={Hash} title="Repeated File Hashes" rows={data.repeated_hashes.map(h => ({ label: h.sha256.slice(0, 24) + '…', count: h.count, mono: true }))} />
      </div>
    </div>
  )
}

function ListPanel({ icon: Icon, title, rows }) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4 text-hata-accent" />
        <p className="text-xs uppercase tracking-wider text-hata-muted font-semibold">{title}</p>
      </div>
      {rows.length === 0 ? (
        <p className="text-xs text-hata-muted py-4 text-center">No data yet.</p>
      ) : (
        <div className="space-y-1.5">
          {rows.map((r, i) => (
            <div key={i} className="flex items-center justify-between text-sm py-1.5 border-b border-hata-border/40 last:border-0">
              <span className={`text-hata-text truncate ${r.mono ? 'mono text-xs' : ''}`}>{r.label}</span>
              <span className="text-hata-accent font-bold text-xs shrink-0 ml-3">{r.count}×</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
