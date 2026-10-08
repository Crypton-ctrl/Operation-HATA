import { AlertTriangle, RefreshCcw } from 'lucide-react'

export default function ErrorPanel({ message, onRetry }) {
  return (
    <div className="glass rounded-xl p-8 flex flex-col items-center text-center gap-3 border-risk-critical/30">
      <AlertTriangle className="w-8 h-8 text-risk-critical" />
      <p className="text-sm font-semibold text-hata-text">Something went wrong loading this page</p>
      <p className="text-xs text-hata-muted max-w-md">{message}</p>
      <p className="text-[11px] text-hata-muted">
        Check that the backend server is running at <code className="mono">http://localhost:8000</code> and check its terminal window for error details.
      </p>
      {onRetry && (
        <button onClick={onRetry}
          className="focus-ring mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-hata-accent text-hata-bg hover:bg-cyan-300 transition-colors">
          <RefreshCcw className="w-4 h-4" /> Try Again
        </button>
      )}
    </div>
  )
}
