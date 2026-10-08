const VARIANTS = {
  safe: { text: 'text-risk-safe', bg: 'bg-risk-safe/10', border: 'border-risk-safe/30', glyph: '✓' },
  suspicious: { text: 'text-risk-medium', bg: 'bg-risk-medium/10', border: 'border-risk-medium/30', glyph: '⚠' },
  dangerous: { text: 'text-risk-critical', bg: 'bg-risk-critical/10', border: 'border-risk-critical/30', glyph: '✕' },
  not_detected: { text: 'text-hata-muted', bg: 'bg-white/5', border: 'border-hata-border', glyph: '—' },
}

export default function StatusPill({ status = 'not_detected', label }) {
  const v = VARIANTS[status] || VARIANTS.not_detected
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${v.text} ${v.bg} ${v.border}`}>
      <span aria-hidden="true">{v.glyph}</span>
      {label}
    </span>
  )
}
