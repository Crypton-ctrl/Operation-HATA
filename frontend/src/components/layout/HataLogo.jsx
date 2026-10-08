import { ShieldHalf } from 'lucide-react'

export default function HataLogo({ compact = false }) {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <div className="relative flex items-center justify-center w-9 h-9 rounded-lg bg-gradient-to-br from-hata-accent to-hata-accent2 shadow-glow shrink-0">
        <ShieldHalf className="w-5 h-5 text-hata-bg" strokeWidth={2.5} />
      </div>
      {!compact && (
        <div className="leading-tight">
          <div className="font-extrabold tracking-wider text-sm text-hata-text">OPERATION HATA</div>
          <div className="text-[10px] tracking-wide text-hata-muted uppercase">Attachment Threat Analyzer</div>
        </div>
      )}
    </div>
  )
}
