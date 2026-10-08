import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { listScans } from '../services/api.js'
import { riskMeta } from '../utils/risk.js'
import ErrorPanel from '../components/common/ErrorPanel.jsx'

const CATEGORIES = ['all', 'SAFE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
const SOURCES = ['all', 'automatic', 'manual']

export default function History() {
  const [scans, setScans] = useState([])
  const [category, setCategory] = useState('all')
  const [source, setSource] = useState('all')
  const [search, setSearch] = useState('')
  const [sortDesc, setSortDesc] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setError(null)
    try {
      const data = await listScans({ category, source, search: search || undefined })
      setScans(data)
    } catch (e) { setError(e.message) }
  }, [category, source, search])

  useEffect(() => { load() }, [load])

  const sorted = [...scans].sort((a, b) => {
    const diff = new Date(a.started_at) - new Date(b.started_at)
    return sortDesc ? -diff : diff
  })

  return (
    <div className="space-y-4">
      {error && <ErrorPanel message={error} onRetry={load} />}

      <div className="glass rounded-xl p-4 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-4 h-4 text-hata-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search filename or sender…"
            className="focus-ring w-full pl-9 pr-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text"
          />
        </div>
        <select value={category} onChange={(e) => setCategory(e.target.value)}
          className="focus-ring px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text">
          {CATEGORIES.map(c => <option key={c} value={c}>{c === 'all' ? 'All Risk Levels' : c}</option>)}
        </select>
        <select value={source} onChange={(e) => setSource(e.target.value)}
          className="focus-ring px-3 py-2 rounded-lg bg-hata-panel2 border border-hata-border text-sm text-hata-text">
          {SOURCES.map(s => <option key={s} value={s}>{s === 'all' ? 'All Sources' : s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
        <button onClick={() => setSortDesc(v => !v)}
          className="focus-ring px-3 py-2 rounded-lg text-sm border border-hata-border text-hata-muted hover:bg-white/5">
          Date {sortDesc ? '↓' : '↑'}
        </button>
      </div>

      <div className="glass rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-hata-border text-left text-[11px] uppercase tracking-wider text-hata-muted">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Filename</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Sender</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-hata-muted text-xs">No scans match the current filters.</td></tr>
              )}
              {sorted.map((s) => {
                const meta = riskMeta(s.risk_category)
                return (
                  <tr key={s.id} className="border-b border-hata-border/50 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 text-xs text-hata-muted whitespace-nowrap">{new Date(s.started_at).toLocaleString()}</td>
                    <td className="px-4 py-3 text-hata-text font-medium max-w-[220px] truncate">{s.filename}</td>
                    <td className="px-4 py-3 text-xs">
                      <span className="px-2 py-0.5 rounded-full border border-hata-border text-hata-muted">{s.source}</span>
                    </td>
                    <td className="px-4 py-3 text-xs text-hata-muted max-w-[180px] truncate">{s.sender || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-bold px-2 py-1 rounded-md ${meta.bg}/10 ${meta.text}`}>{s.risk_category}</span>
                    </td>
                    <td className="px-4 py-3 mono font-semibold text-hata-text">{s.risk_score}</td>
                    <td className="px-4 py-3 text-xs text-hata-muted">{s.status}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => navigate(`/scan-result/${s.id}`)}
                        className="focus-ring text-xs text-hata-accent hover:underline">View</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
