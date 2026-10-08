import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, Trash2, RotateCcw, Eye } from 'lucide-react'
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

  return (
    <div className="space-y-4">
      {error && <div className="rounded-lg border border-risk-critical/40 bg-risk-critical/10 text-risk-critical text-sm p-3">{error}</div>}

      <div className="glass rounded-xl overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-hata-border">
          <Lock className="w-4 h-4 text-hata-accent" />
          <h3 className="text-sm font-semibold text-hata-text">Quarantined Attachments ({items.filter(i => i.status === 'quarantined').length})</h3>
        </div>
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
              {items.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-hata-muted text-xs">Quarantine is empty.</td></tr>
              )}
              {items.map((item) => {
                const meta = riskMeta(item.risk_category)
                return (
                  <tr key={item.id} className="border-b border-hata-border/50 hover:bg-white/5">
                    <td className="px-4 py-3 text-hata-text font-medium max-w-[180px] truncate">{item.filename}</td>
                    <td className="px-4 py-3 mono text-[10px] text-hata-muted max-w-[140px] truncate">{item.sha256}</td>
                    <td className="px-4 py-3"><span className={`text-xs font-bold px-2 py-1 rounded-md ${meta.bg}/10 ${meta.text}`}>{item.risk_category}</span></td>
                    <td className="px-4 py-3 text-xs text-hata-muted whitespace-nowrap">{new Date(item.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-xs text-hata-muted">{item.source}</td>
                    <td className="px-4 py-3 text-xs text-hata-muted max-w-[220px] truncate">{item.reason}</td>
                    <td className="px-4 py-3 text-xs">
                      <span className={item.status === 'quarantined' ? 'text-risk-medium' : item.status === 'restored' ? 'text-risk-safe' : 'text-hata-muted'}>
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
