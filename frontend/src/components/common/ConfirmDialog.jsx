export default function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', danger = true, onConfirm, onCancel }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" role="dialog" aria-modal="true">
      <div className="glass rounded-xl w-full max-w-sm p-5">
        <h3 className="text-base font-bold text-hata-text mb-2">{title}</h3>
        <p className="text-sm text-hata-muted mb-5">{message}</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="focus-ring px-4 py-2 rounded-lg text-sm font-medium border border-hata-border text-hata-text hover:bg-white/5">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`focus-ring px-4 py-2 rounded-lg text-sm font-semibold text-white ${danger ? 'bg-risk-critical hover:bg-red-600' : 'bg-hata-accent2 hover:bg-cyan-600'}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
