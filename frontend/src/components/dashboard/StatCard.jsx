export default function StatCard({ icon: Icon, label, value, tone = 'default', hint }) {
  const toneMap = {
    default: 'text-hata-accent border-hata-border',
    safe: 'text-risk-safe border-risk-safe/30',
    warn: 'text-risk-medium border-risk-medium/30',
    danger: 'text-risk-critical border-risk-critical/30',
  }
  return (
    <div className="glass rounded-xl p-4 flex items-center justify-between hover:border-hata-accent/30 transition-colors">
      <div>
        <p className="text-[11px] uppercase tracking-wider text-hata-muted font-medium">{label}</p>
        <p className="text-2xl font-extrabold mt-1 text-hata-text">{value}</p>
        {hint && <p className="text-[11px] text-hata-muted mt-0.5">{hint}</p>}
      </div>
      <div className={`w-11 h-11 rounded-lg border flex items-center justify-center ${toneMap[tone]}`}>
        <Icon className="w-5 h-5" />
      </div>
    </div>
  )
}
