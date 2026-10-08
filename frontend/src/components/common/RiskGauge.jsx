import { riskMeta } from '../../utils/risk.js'

export default function RiskGauge({ score = 0, category = 'SAFE', size = 200 }) {
  const meta = riskMeta(category)
  const Icon = meta.icon
  const radius = (size - 24) / 2
  const circumference = 2 * Math.PI * radius
  const pct = Math.max(0, Math.min(100, score)) / 100
  const offset = circumference * (1 - pct)

  return (
    <div className={`relative flex items-center justify-center rounded-full ${meta.glow}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#1c2333" strokeWidth="12" />
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke={meta.color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1s ease-out, stroke 0.5s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <Icon className="w-7 h-7 mb-1" style={{ color: meta.color }} strokeWidth={2} />
        <div className="text-3xl font-extrabold mono" style={{ color: meta.color }}>{score}</div>
        <div className="text-[10px] text-hata-muted -mt-0.5">/ 100</div>
        <div className="mt-1 text-[11px] font-bold tracking-wider" style={{ color: meta.color }}>{meta.label}</div>
      </div>
    </div>
  )
}
