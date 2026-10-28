import { useState, useCallback, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { 
  UploadCloud, FileImage, Loader2, CheckCircle2, AlertTriangle, 
  ShieldAlert, ShieldCheck, Lock, Eye, Trash2, PlayCircle, RefreshCw 
} from 'lucide-react'
import { uploadScan, startScan, getScan } from '../services/api.js'
import { useHataSocket } from '../hooks/useHataSocket.js'
import AnalysisTimeline from '../components/scanner/AnalysisTimeline.jsx'
import { riskMeta } from '../utils/risk.js'

const SUPPORTED = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp']
const SUPPORTED_EXT = 'JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP'

export default function ManualScan() {
  const [dragActive, setDragActive] = useState(false)
  const [batchQueue, setBatchQueue] = useState([]) // Array of file objects
  const [isBatchMode, setIsBatchMode] = useState(false)
  const [error, setError] = useState(null)
  
  // Single file state
  const [singleFile, setSingleFile] = useState(null)
  const [singleUploadResult, setSingleUploadResult] = useState(null)
  const [phase, setPhase] = useState('idle') // idle | uploading | ready | running | failed
  const [currentStage, setCurrentStage] = useState(null)
  
  // Batch scanning state
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchCurrentIndex, setBatchCurrentIndex] = useState(-1)
  const [batchComplete, setBatchComplete] = useState(false)

  const inputRef = useRef(null)
  const navigate = useNavigate()

  useHataSocket((msg) => {
    // Handle single file progress
    if (!isBatchMode && msg.type === 'scan_progress' && singleUploadResult && msg.data.scan_id === singleUploadResult.scan_id) {
      setCurrentStage(msg.data.stage)
      if (msg.data.stage === 'complete' && msg.data.status === 'complete') {
        setTimeout(() => navigate(`/scan-result/${singleUploadResult.scan_id}`), 700)
      }
      if (msg.data.status === 'failed') {
        setPhase('failed')
        setError(msg.data.error || 'Analysis failed unexpectedly.')
      }
    }

    // Handle batch item update
    if (isBatchMode && msg.type === 'scan_progress') {
      setBatchQueue((prev) =>
        prev.map((item) => {
          if (item.scan_id === msg.data.scan_id) {
            return {
              ...item,
              currentStage: msg.data.stage,
              status: msg.data.status === 'complete' ? 'complete' : item.status,
            }
          }
          return item
        })
      )
    }
  })

  const resetAll = () => {
    setSingleFile(null)
    setSingleUploadResult(null)
    setError(null)
    setPhase('idle')
    setCurrentStage(null)
    setBatchQueue([])
    setIsBatchMode(false)
    setBatchRunning(false)
    setBatchCurrentIndex(-1)
    setBatchComplete(false)
  }

  const handleSelectedFiles = useCallback(async (filesList) => {
    setError(null)
    if (!filesList || filesList.length === 0) return

    const selected = Array.from(filesList)

    if (selected.length === 1) {
      // Single file workflow
      setIsBatchMode(false)
      const file = selected[0]
      setSingleFile(file)
      setPhase('uploading')
      try {
        const result = await uploadScan(file)
        setSingleUploadResult(result)
        setPhase('ready')
      } catch (e) {
        setError(e.message)
        setPhase('idle')
        setSingleFile(null)
      }
    } else {
      // Multiple files batch workflow
      setIsBatchMode(true)
      setBatchComplete(false)
      const initialQueue = selected.map((f, idx) => ({
        id: `batch-${Date.now()}-${idx}`,
        file: f,
        filename: f.name,
        size_bytes: f.size,
        status: 'pending', // pending | uploading | scanning | complete | failed
        scan_id: null,
        detected_format: null,
        risk_category: null,
        risk_score: null,
        is_quarantined: false,
        error: null,
      }))
      setBatchQueue(initialQueue)
      setPhase('ready')
    }
  }, [])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files?.length > 0) {
      handleSelectedFiles(e.dataTransfer.files)
    }
  }

  const handleStartSingle = async () => {
    if (!singleUploadResult) return
    setPhase('running')
    setCurrentStage('file_received')
    try {
      await startScan(singleUploadResult.scan_id)
    } catch (e) {
      setPhase('failed')
      setError(e.message)
    }
  }

  const handleStartBatch = async () => {
    if (batchQueue.length === 0 || batchRunning) return
    setBatchRunning(true)
    setError(null)

    for (let i = 0; i < batchQueue.length; i++) {
      setBatchCurrentIndex(i)
      const item = batchQueue[i]

      // Step 1: Upload file
      setBatchQueue((prev) =>
        prev.map((it, idx) => (idx === i ? { ...it, status: 'uploading' } : it))
      )

      let uploadRes = null
      try {
        uploadRes = await uploadScan(item.file)
        setBatchQueue((prev) =>
          prev.map((it, idx) =>
            idx === i
              ? {
                  ...it,
                  scan_id: uploadRes.scan_id,
                  detected_format: uploadRes.detected_format,
                  status: 'scanning',
                }
              : it
          )
        )
      } catch (upErr) {
        setBatchQueue((prev) =>
          prev.map((it, idx) =>
            idx === i ? { ...it, status: 'failed', error: upErr.message } : it
          )
        )
        continue
      }

      // Step 2: Start scan and poll till completion
      try {
        await startScan(uploadRes.scan_id)

        // Poll for completion
        let done = false
        let attempts = 0
        while (!done && attempts < 30) {
          attempts++
          await new Promise((r) => setTimeout(r, 1000))
          try {
            const scanData = await getScan(uploadRes.scan_id)
            if (scanData?.scan?.status === 'complete') {
              done = true
              const riskCat = scanData.risk?.category || 'SAFE'
              const riskScore = scanData.risk?.total_score || 0
              const isQ = Boolean(scanData.quarantine_item && scanData.quarantine_item.status === 'quarantined')

              setBatchQueue((prev) =>
                prev.map((it, idx) =>
                  idx === i
                    ? {
                        ...it,
                        status: 'complete',
                        risk_category: riskCat,
                        risk_score: riskScore,
                        is_quarantined: isQ,
                      }
                    : it
                )
              )
            } else if (scanData?.scan?.status === 'failed') {
              done = true
              setBatchQueue((prev) =>
                prev.map((it, idx) =>
                  idx === i ? { ...it, status: 'failed', error: 'Scan pipeline failed' } : it
                )
              )
            }
          } catch {
            // keep waiting
          }
        }
      } catch (startErr) {
        setBatchQueue((prev) =>
          prev.map((it, idx) =>
            idx === i ? { ...it, status: 'failed', error: startErr.message } : it
          )
        )
      }
    }

    setBatchRunning(false)
    setBatchComplete(true)
    setBatchCurrentIndex(-1)
  }

  // Count quarantined threats in batch
  const quarantinedCount = batchQueue.filter(
    (b) => b.is_quarantined || (b.risk_category && ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(b.risk_category) && b.risk_score >= 20)
  ).length
  const safeCount = batchQueue.filter((b) => b.status === 'complete' && b.risk_category === 'SAFE').length

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
            ref={inputRef} 
            type="file" 
            multiple 
            className="hidden" 
            accept={SUPPORTED.join(',')}
            onChange={(e) => handleSelectedFiles(e.target.files)}
          />
          <UploadCloud className="w-12 h-12 text-hata-accent mb-4" />
          <p className="text-lg font-semibold text-hata-text">Drop images here</p>
          <p className="text-sm text-hata-muted mt-1">or click to browse multiple files</p>
          <span className="mt-4 px-3 py-1 rounded-full text-[11px] font-semibold bg-hata-panel2 border border-hata-border text-hata-accent">
            Multi-file batch scanning supported
          </span>
          <p className="text-xs text-hata-muted mt-4">Supported formats: {SUPPORTED_EXT}</p>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-risk-critical/40 bg-risk-critical/10 text-risk-critical text-sm p-4">
          {error}
        </div>
      )}

      {/* SINGLE FILE READY CARD */}
      {!isBatchMode && phase === 'ready' && singleUploadResult && (
        <div className="glass rounded-2xl p-6 space-y-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-hata-accent/10 flex items-center justify-center shrink-0">
              <FileImage className="w-6 h-6 text-hata-accent" />
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-hata-text truncate">{singleUploadResult.filename}</p>
              <p className="text-xs text-hata-muted">
                {(singleUploadResult.size_bytes / 1024).toFixed(1)} KB &middot; Detected format: {singleUploadResult.detected_format}
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <button 
              onClick={handleStartSingle}
              className="focus-ring flex-1 py-3 rounded-lg font-semibold text-sm bg-hata-accent text-hata-bg hover:opacity-90 transition-colors shadow-sm"
            >
              START ANALYSIS
            </button>
            <button 
              onClick={resetAll}
              className="focus-ring px-4 py-3 rounded-lg font-medium text-sm border border-hata-border text-hata-muted hover:bg-white/5"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* SINGLE FILE TIMELINE */}
      {!isBatchMode && (phase === 'running' || phase === 'failed') && (
        <AnalysisTimeline currentStage={currentStage} failed={phase === 'failed'} />
      )}

      {/* MULTI-FILE BATCH QUEUE */}
      {isBatchMode && batchQueue.length > 0 && (
        <div className="glass rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-hata-border">
            <div>
              <h3 className="text-base font-semibold text-hata-text flex items-center gap-2">
                <FileImage className="w-5 h-5 text-hata-accent" />
                Batch Scan Queue ({batchQueue.length} Files)
              </h3>
              <p className="text-xs text-hata-muted mt-0.5">
                Files will be analyzed sequentially and automatically quarantined upon threat detection.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {!batchRunning && !batchComplete && (
                <button
                  onClick={handleStartBatch}
                  className="focus-ring px-4 py-2 rounded-lg text-sm font-bold bg-hata-accent text-hata-bg hover:opacity-90 transition-colors shadow-sm flex items-center gap-2"
                >
                  <PlayCircle className="w-4 h-4" /> Start Batch Analysis ({batchQueue.length})
                </button>
              )}
              {!batchRunning && (
                <button
                  onClick={resetAll}
                  className="focus-ring px-3.5 py-2 rounded-lg text-xs font-semibold border border-hata-border text-hata-muted hover:bg-white/5"
                >
                  Clear Queue
                </button>
              )}
            </div>
          </div>

          {/* Batch Completion Summary */}
          {batchComplete && (
            <div className="p-4 rounded-xl bg-hata-panel2 border border-hata-border flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-6 h-6 text-risk-safe" />
                <div>
                  <h4 className="text-sm font-semibold text-hata-text">Batch Scan Completed!</h4>
                  <p className="text-xs text-hata-muted">
                    {safeCount} clean file{safeCount === 1 ? '' : 's'} verified &middot; {quarantinedCount} threat file{quarantinedCount === 1 ? '' : 's'} isolated in quarantine.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {quarantinedCount > 0 && (
                  <Link
                    to="/quarantine"
                    className="focus-ring px-3.5 py-1.5 rounded-lg text-xs font-bold bg-risk-critical/15 text-risk-critical border border-risk-critical/30 hover:bg-risk-critical/20 flex items-center gap-1.5"
                  >
                    <Lock className="w-3.5 h-3.5" /> View Quarantined Files ({quarantinedCount})
                  </Link>
                )}
                <Link
                  to="/history"
                  className="focus-ring px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-hata-panel border border-hata-border text-hata-text hover:bg-white/5"
                >
                  View Scan History
                </Link>
              </div>
            </div>
          )}

          {/* File Queue List */}
          <div className="divide-y divide-hata-border/40 max-h-[420px] overflow-y-auto pr-1">
            {batchQueue.map((item, idx) => {
              const meta = item.risk_category ? riskMeta(item.risk_category) : null
              const isCurrent = batchCurrentIndex === idx

              return (
                <div key={item.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="w-9 h-9 rounded-lg bg-hata-panel2 border border-hata-border flex items-center justify-center shrink-0">
                      <FileImage className="w-4 h-4 text-hata-muted" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-hata-text truncate">{item.filename}</p>
                      <p className="text-[11px] text-hata-muted">
                        {(item.size_bytes / 1024).toFixed(1)} KB
                        {item.detected_format && ` · ${item.detected_format}`}
                      </p>
                    </div>
                  </div>

                  {/* Status / Results Badge */}
                  <div className="flex items-center gap-2 shrink-0">
                    {item.status === 'pending' && (
                      <span className="text-xs text-hata-muted bg-hata-panel px-2.5 py-1 rounded-md border border-hata-border">
                        Queued
                      </span>
                    )}

                    {item.status === 'uploading' && (
                      <span className="text-xs text-hata-accent bg-hata-accent/10 px-2.5 py-1 rounded-md border border-hata-accent/30 flex items-center gap-1.5">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Uploading…
                      </span>
                    )}

                    {item.status === 'scanning' && (
                      <span className="text-xs text-hata-accent bg-hata-accent/10 px-2.5 py-1 rounded-md border border-hata-accent/30 flex items-center gap-1.5">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        {item.currentStage ? item.currentStage.replace(/_/g, ' ') : 'Analyzing…'}
                      </span>
                    )}

                    {item.status === 'complete' && meta && (
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold px-2.5 py-1 rounded-md ${meta.bg}/15 ${meta.text} border ${meta.border}/30`}>
                          {item.risk_category} ({item.risk_score}/100)
                        </span>
                        {(item.is_quarantined || (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(item.risk_category) && item.risk_score >= 20)) && (
                          <span className="text-xs font-semibold px-2 py-1 rounded-md bg-risk-critical/15 text-risk-critical border border-risk-critical/30 flex items-center gap-1">
                            <Lock className="w-3 h-3" /> Quarantined
                          </span>
                        )}
                        {item.scan_id && (
                          <button
                            title="View Full Report"
                            onClick={() => navigate(`/scan-result/${item.scan_id}`)}
                            className="p-1 rounded-md text-hata-muted hover:text-hata-accent hover:bg-white/5 transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    )}

                    {item.status === 'failed' && (
                      <span className="text-xs text-risk-critical bg-risk-critical/10 px-2.5 py-1 rounded-md border border-risk-critical/30">
                        Failed
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
