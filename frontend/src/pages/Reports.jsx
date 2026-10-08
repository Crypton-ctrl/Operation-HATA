import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Download, Eye } from 'lucide-react'
import { listScans, downloadPdfReport } from '../services/api.js'
import { riskMeta } from '../utils/risk.js'
import ErrorPanel from '../components/common/ErrorPanel.jsx'

export default function Reports() {
  const [scans, setScans] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [downloadingId, setDownloadingId] = useState(null)
  const navigate = useNavigate()

  const load = () => {
    setLoading(true); setError(null)
    listScans({}).then((data) => {
      setScans(data.filter(s => s.status === 'complete'))
      setLoading(false)
    }).catch((e) => { setError(e.message); setLoading(false) })
  }

  useEffect(() => { load() }, [])

  const handleDownload = async (scanId) => {
    setDownloadingId(scanId)
    try { await downloadPdfReport(scanId) } catch (e) { setError(e.message) }
    setDownloadingId(null)
  }

  if (loading) return <div className="text-hata-muted text-sm">Loading reports…</div>
  if (error) return <ErrorPanel message={error} onRetry={load} />

  return (
    <div className="space-y-4">
      <p className="text-sm text-hata-muted">
        Every completed scan produces a full AI security report, viewable here or downloadable as a branded PDF.
      </p>

      {scans.length === 0 ? (
        <div className="glass rounded-xl p-10 text-center text-hata-muted text-sm">
          No completed scans yet. Run a Manual Scan or connect email monitoring to generate reports.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {scans.map((s) => {
            const meta = riskMeta(s.risk_category)
            return (
              <div key={s.id} className="glass rounded-xl p-5 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText className="w-5 h-5 text-hata-accent shrink-0" />
                    <div className="min-w-0">
                      <p className="font-semibold text-hata-text truncate">{s.filename}</p>
                      <p className="text-[11px] text-hata-muted">{new Date(s.started_at).toLocaleString()}</p>
                    </div>
                  </div>
                  <span className={`shrink-0 text-xs font-bold px-2 py-1 rounded-md ${meta.bg}/10 ${meta.text}`}>
                    {s.risk_category} · {s.risk_score}
                  </span>
                </div>
                <div className="flex gap-2 mt-1">
                  <button onClick={() => navigate(`/scan-result/${s.id}`)}
                    className="focus-ring flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border border-hata-border text-hata-text hover:bg-white/5">
                    <Eye className="w-3.5 h-3.5" /> View
                  </button>
                  <button onClick={() => handleDownload(s.id)} disabled={downloadingId === s.id}
                    className="focus-ring flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-hata-accent text-hata-bg hover:bg-cyan-300 disabled:opacity-50">
                    <Download className="w-3.5 h-3.5" /> {downloadingId === s.id ? 'Preparing…' : 'PDF'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
