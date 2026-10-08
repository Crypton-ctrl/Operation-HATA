import StatusPill from './StatusPill.jsx'

export default function FindingCard({ title, icon: Icon, status, statusLabel, children, tooltip }) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="w-4 h-4 text-hata-accent" />}
          <h3 className="text-sm font-semibold text-hata-text" title={tooltip}>{title}</h3>
        </div>
        <StatusPill status={status} label={statusLabel} />
      </div>
      <div className="text-xs text-hata-muted space-y-1.5">{children}</div>
    </div>
  )
}
