import { Check, Loader2, Circle, X } from 'lucide-react'

const STAGE_LABELS = {
  file_received: 'File received',
  signature_check: 'File signature verified',
  hash_generation: 'Hash generated',
  metadata_analysis: 'Metadata analyzed',
  entropy_analysis: 'Entropy analysis',
  steganography_analysis: 'Steganography analysis',
  embedded_data_analysis: 'Embedded/appended data scan',
  yara_scan: 'YARA scan',
  ocr_analysis: 'OCR analysis',
  qr_analysis: 'QR code analysis',
  url_analysis: 'URL analysis',
  risk_calculation: 'Risk score calculated',
  ai_assessment: 'AI assessment',
  complete: 'Analysis complete',
}

const ORDER = Object.keys(STAGE_LABELS)

export default function AnalysisTimeline({ currentStage, failed }) {
  const currentIdx = ORDER.indexOf(currentStage)

  return (
    <div className="glass rounded-xl p-5">
      <h3 className="text-sm font-semibold mb-4 text-hata-text">Live Analysis</h3>
      <ul className="space-y-2.5">
        {ORDER.map((stage, idx) => {
          let state = 'pending'
          if (failed && idx === currentIdx) state = 'failed'
          else if (idx < currentIdx || (stage === 'complete' && currentStage === 'complete')) state = 'done'
          else if (idx === currentIdx) state = 'active'

          return (
            <li key={stage} className="flex items-center gap-3 text-sm">
              {state === 'done' && <Check className="w-4 h-4 text-risk-safe shrink-0" />}
              {state === 'active' && <Loader2 className="w-4 h-4 text-hata-accent shrink-0 animate-spin" />}
              {state === 'pending' && <Circle className="w-4 h-4 text-hata-border shrink-0" />}
              {state === 'failed' && <X className="w-4 h-4 text-risk-critical shrink-0" />}
              <span className={
                state === 'done' ? 'text-hata-text' :
                state === 'active' ? 'text-hata-accent font-medium' :
                state === 'failed' ? 'text-risk-critical font-medium' : 'text-hata-muted'
              }>
                {STAGE_LABELS[stage]}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
