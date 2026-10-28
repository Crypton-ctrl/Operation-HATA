import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, Trash2, RotateCcw, Eye, ShieldCheck, ShieldAlert, Sparkles } from 'lucide-react'
import { listQuarantine, deleteQuarantineItem, restoreQuarantineItem } from '../services/api.js'
import { riskMeta } from '../utils/risk.js'
import ConfirmDialog from '../components/common/ConfirmDialog.jsx'
import ErrorPanel from '../components/common/ErrorPanel.jsx'

export default function Quarantine() {
  const [items, setItems] = useState([])
  const [confirmAction, setConfirmAction] = useState(null) // { type, item }
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = useCallback(async () => {
    setError(null)
    try { setItems(await listQuarantine()) } catch (e) { setError(e.message) }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const handleConfirm = async () => {
    if (!confirmAction) return
    setError(null)
    try {
      if (confirmAction.type === 'delete') await deleteQuarantineItem(confirmAction.item.id)
      if (confirmAction.type === 'restore') await restoreQuarantineItem(confirmAction.item.id)
      await load()
    } catch (e) { setError(e.message) }
    setConfirmAction(null)
  }

  if (loading) return <div className="text-hata-muted text-sm">Loading quarantine…</div>
  if (error && items.length === 0) return <ErrorPanel message={error} onRetry={load} />

  const quarantinedCount = items.filter(i => i.status === 'quarantined').length

  return (
    <div className="space-y-4">
      {error && <div className="rounded-lg border border-risk-critical/40 bg-risk-critical/10 text-risk-critical text-sm p-3">{error}</div>}

      <div className="glass rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-hata-border flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-hata-accent" />
            <h3 className="text-sm font-semibold text-hata-text">Quarantined Attachments ({quarantinedCount})</h3>
          </div>
          <p className="text-[11px] text-hata-muted">
            Files with threat indicators (score ≥ 20, embedded payloads, or stego) are automatically isolated here.
          </p>
        </div>

        {items.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto text-emerald-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-semibold text-hata-text">Quarantine is Currently Empty</h4>
            <p className="text-xs text-hata-muted max-w-md mx-auto leading-relaxed">
              Safe attachments are not quarantined. Only files presenting verified threat indicators (such as hidden executables, embedded archives, YARA rule hits, or risk score ≥ 20) are placed into isolation.
            </p>
            <div className="pt-2">
              <button
                onClick={() => navigate('/manual-scan')}
                className="focus-ring inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-hata-accent text-hata-bg hover:bg-cyan-300 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" /> Scan Files Now
              </button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-hata-border text-left text-[11px] uppercase tracking-wider text-hata-muted">
                  <th className="px-4 py-3">Filename</th>
                  <th className="px-4 py-3">SHA-256</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Reason</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const meta = riskMeta(item.risk_category)
                  return (
                    <tr key={item.id} className="border-b border-hata-border/50 hover:bg-white/5">
                      <td className="px-4 py-3 text-hata-text font-medium max-w-[180px] truncate" title={item.filename}>{item.filename}</td>
                      <td className="px-4 py-3 mono text-[10px] text-hata-muted max-w-[140px] truncate" title={item.sha256}>{item.sha256}</td>
                      <td className="px-4 py-3"><span className={`text-xs font-bold px-2 py-1 rounded-md ${meta.bg}/10 ${meta.text}`}>{item.risk_category}</span></td>
                      <td className="px-4 py-3 text-xs text-hata-muted whitespace-nowrap">{new Date(item.created_at).toLocaleDateString()}</td>
                      <td className="px-4 py-3 text-xs text-hata-muted">{item.source}</td>
                      <td className="px-4 py-3 text-xs text-hata-muted max-w-[220px] truncate" title={item.reason}>{item.reason}</td>
                      <td className="px-4 py-3 text-xs">
                        <span className={item.status === 'quarantined' ? 'text-risk-medium font-semibold' : item.status === 'restored' ? 'text-risk-safe' : 'text-hata-muted'}>
                          {item.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button title="View Report" onClick={() => navigate(`/scan-result/${item.scan_id}`)}
                            className="focus-ring p-1.5 rounded-md hover:bg-white/10 text-hata-muted hover:text-hata-accent">
                            <Eye className="w-4 h-4" />
                          </button>
                          {item.status === 'quarantined' && (
                            <>
                              <button title="Restore" onClick={() => setConfirmAction({ type: 'restore', item })}
                                className="focus-ring p-1.5 rounded-md hover:bg-white/10 text-hata-muted hover:text-risk-safe">
                                <RotateCcw className="w-4 h-4" />
                              </button>
                              <button title="Delete" onClick={() => setConfirmAction({ type: 'delete', item })}
                                className="focus-ring p-1.5 rounded-md hover:bg-white/10 text-hata-muted hover:text-risk-critical">
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!confirmAction}
        title={confirmAction?.type === 'delete' ? 'Delete quarantined file?' : 'Restore quarantined file?'}
        message={
          confirmAction?.type === 'delete'
            ? `This will permanently delete "${confirmAction?.item?.filename}" from quarantine. This action cannot be undone.`
            : `Restoring "${confirmAction?.item?.filename}" will mark it as safe to release from isolation. Only do this after reviewing the full report.`
        }
        confirmLabel={confirmAction?.type === 'delete' ? 'Delete Permanently' : 'Restore'}
        danger={confirmAction?.type === 'delete'}
        onConfirm={handleConfirm}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  )
}
