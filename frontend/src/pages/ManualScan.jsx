import { useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadCloud, FileImage, Loader2 } from 'lucide-react'
import { uploadScan, startScan } from '../services/api.js'
import { useHataSocket } from '../hooks/useHataSocket.js'
import AnalysisTimeline from '../components/scanner/AnalysisTimeline.jsx'

const SUPPORTED = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp']
const SUPPORTED_EXT = 'JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP'

export default function ManualScan() {
  const [dragActive, setDragActive] = useState(false)
  const [file, setFile] = useState(null)
  const [uploadResult, setUploadResult] = useState(null)
  const [error, setError] = useState(null)
  const [phase, setPhase] = useState('idle') // idle | uploading | ready | running | failed
  const [currentStage, setCurrentStage] = useState(null)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  useHataSocket((msg) => {
    if (msg.type === 'scan_progress' && uploadResult && msg.data.scan_id === uploadResult.scan_id) {
      setCurrentStage(msg.data.stage)
      if (msg.data.stage === 'complete' && msg.data.status === 'complete') {
        setTimeout(() => navigate(`/scan-result/${uploadResult.scan_id}`), 700)
      }
      if (msg.data.status === 'failed') {
        setPhase('failed')
        setError(msg.data.error || 'Analysis failed unexpectedly.')
      }
    }
  })

  const resetAll = () => {
    setFile(null); setUploadResult(null); setError(null); setPhase('idle'); setCurrentStage(null)
  }

  const handleFile = useCallback(async (selected) => {
    setError(null)
    if (!selected) return
    setFile(selected)
    setPhase('uploading')
    try {
      const result = await uploadScan(selected)
      setUploadResult(result)
      setPhase('ready')
    } catch (e) {
      setError(e.message)
      setPhase('idle')
      setFile(null)
    }
  }, [])

  const handleDrop = (e) => {
    e.preventDefault(); setDragActive(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleFile(f)
  }

  const handleStart = async () => {
    if (!uploadResult) return
    setPhase('running')
    setCurrentStage('file_received')
    try {
      await startScan(uploadResult.scan_id)
    } catch (e) {
      setPhase('failed')
      setError(e.message)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {phase === 'idle' && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`glass rounded-2xl border-2 border-dashed transition-colors p-14 flex flex-col items-center justify-center text-center cursor-pointer ${
            dragActive ? 'border-hata-accent bg-hata-accent/5' : 'border-hata-border'
          }`}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef} type="file" className="hidden" accept={SUPPORTED.join(',')}
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          <UploadCloud className="w-12 h-12 text-hata-accent mb-4" />
          <p className="text-lg font-semibold text-hata-text">Drop image here</p>
          <p className="text-sm text-hata-muted mt-1">or click to browse files</p>
          <p className="text-xs text-hata-muted mt-6">Supported: {SUPPORTED_EXT}</p>
        </div>
      )}

      {phase === 'uploading' && (
        <div className="glass rounded-2xl p-14 flex flex-col items-center justify-center text-center">
          <Loader2 className="w-8 h-8 text-hata-accent animate-spin mb-3" />
          <p className="text-sm text-hata-muted">Validating and quarantining file…</p>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-risk-critical/40 bg-risk-critical/10 text-risk-critical text-sm p-4">
          {error}
        </div>
      )}

      {phase === 'ready' && uploadResult && (
        <div className="glass rounded-2xl p-6 space-y-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-hata-accent/10 flex items-center justify-center shrink-0">
              <FileImage className="w-6 h-6 text-hata-accent" />
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-hata-text truncate">{uploadResult.filename}</p>
              <p className="text-xs text-hata-muted">
                {(uploadResult.size_bytes / 1024).toFixed(1)} KB &middot; Detected format: {uploadResult.detected_format}
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={handleStart}
              className="focus-ring flex-1 py-3 rounded-lg font-semibold text-sm bg-hata-accent text-hata-bg hover:bg-cyan-300 transition-colors">
              START ANALYSIS
            </button>
            <button onClick={resetAll}
              className="focus-ring px-4 py-3 rounded-lg font-medium text-sm border border-hata-border text-hata-muted hover:bg-white/5">
              Cancel
            </button>
          </div>
        </div>
      )}

      {(phase === 'running' || phase === 'failed') && (
        <AnalysisTimeline currentStage={currentStage} failed={phase === 'failed'} />
      )}
    </div>
  )
}
