import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  FileSignature, Fingerprint, Camera, Activity, EyeOff, FileWarning,
  ScanLine, TextSearch, QrCode, Globe2, BrainCircuit, Download, ArrowLeft,
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { getScan, downloadPdfReport } from '../services/api.js'
import RiskGauge from '../components/common/RiskGauge.jsx'
import FindingCard from '../components/common/FindingCard.jsx'
import { riskMeta } from '../utils/risk.js'

function pill(status) {
  // maps backend booleans/classifications into safe/suspicious/dangerous/not_detected
  return status
}

export default function ScanResult() {
  const { scanId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const d = await getScan(scanId)
        if (!cancelled) setData(d)
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    }
    load()
    const interval = setInterval(load, 4000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [scanId])

  if (error) return <div className="text-risk-critical text-sm">{error}</div>
  if (!data) return <div className="text-hata-muted text-sm">Loading scan results…</div>

  const { scan, attachment, email, signature, hashes, metadata, entropy, stego,
          embedded, yara, ocr, qr, url_results, risk, ai_report } = data

  const meta = riskMeta(risk?.category || 'UNKNOWN')

  const handleDownload = async () => {
    setDownloading(true)
    try { await downloadPdfReport(scanId, `HATA_Report_${scanId}.pdf`) }
    catch (e) { setError(e.message) }
    setDownloading(false)
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <Link to="/history" className="focus-ring inline-flex items-center gap-1.5 text-sm text-hata-muted hover:text-hata-text">
          <ArrowLeft className="w-4 h-4" /> Back to history
        </Link>
        {scan.status === 'complete' && (
          <button onClick={handleDownload} disabled={downloading}
             className="focus-ring inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-hata-accent text-hata-bg hover:bg-cyan-300 transition-colors disabled:opacity-50">
            <Download className="w-4 h-4" /> {downloading ? 'Preparing PDF…' : 'Download PDF Report'}
          </button>
        )}
      </div>

      {/* Main risk panel */}
      <div className={`glass rounded-2xl p-8 flex flex-col md:flex-row items-center gap-8 border ${meta.border}/30`}>
        <RiskGauge score={risk?.total_score ?? 0} category={risk?.category ?? 'UNKNOWN'} size={180} />
        <div className="flex-1 min-w-0">
          <p className="text-xs uppercase tracking-widest text-hata-muted font-semibold mb-1">Attachment Security Status</p>
          <h2 className="text-2xl font-extrabold text-hata-text truncate">{attachment?.original_filename}</h2>
          <div className="flex flex-wrap gap-x-6 gap-y-1 mt-3 text-xs text-hata-muted">
            <span>Size: {(attachment?.size_bytes / 1024).toFixed(1)} KB</span>
            <span>Source: {attachment?.source?.toUpperCase()}</span>
            {email && <span>Sender: {email.sender}</span>}
            <span>Scanned: {new Date(scan.started_at).toLocaleString()}</span>
          </div>
          {scan.status !== 'complete' && (
            <p className="mt-3 text-sm text-hata-accent">Scan status: {scan.status} — stage: {scan.current_stage}</p>
          )}
        </div>
      </div>

      {scan.status === 'complete' && (
        <>
          {/* AI Assessment */}
          <div className="glass rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <BrainCircuit className="w-5 h-5 text-hata-accent" />
              <h3 className="font-semibold text-hata-text">AI Security Assessment</h3>
              {!ai_report?.ai_available && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-hata-muted/20 text-hata-muted">AI unavailable — technical fallback</span>
              )}
            </div>
            <p className="text-sm text-hata-text mb-3">{ai_report?.executive_summary}</p>
            <div className="grid md:grid-cols-2 gap-4 text-xs text-hata-muted">
              <div><span className="font-semibold text-hata-text">Assessment: </span>{ai_report?.assessment}</div>
              <div><span className="font-semibold text-hata-text">Likely Scenario: </span>{ai_report?.likely_scenario}</div>
              <div><span className="font-semibold text-hata-text">Recommendation: </span>{ai_report?.recommendation}</div>
              <div><span className="font-semibold text-hata-text">AI Accuracy: </span>{ai_report?.confidence}</div>
            </div>
            <p className="text-[11px] text-hata-muted mt-3 italic">{ai_report?.limitations}</p>
          </div>

          {/* Contributing factors */}
          {risk?.contributing_factors?.length > 0 && (
            <div className="glass rounded-2xl p-6">
              <h3 className="font-semibold text-hata-text mb-3">Risk Score Breakdown</h3>
              <div className="space-y-2">
                {risk.contributing_factors.map((f, i) => (
                  <div key={i} className="flex items-center justify-between text-sm border-b border-hata-border/50 pb-2 last:border-0">
                    <div>
                      <p className="text-hata-text font-medium">{f.factor}</p>
                      <p className="text-xs text-hata-muted">{f.reason}</p>
                    </div>
                    <span className="text-risk-high font-bold shrink-0 ml-4">+{f.points}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Finding cards grid */}
          <div className="grid md:grid-cols-2 gap-4">
            <FindingCard title="File Signature" icon={FileSignature}
              status={signature?.status === 'SAFE' ? 'safe' : 'dangerous'}
              statusLabel={signature?.status}>
              <p>Extension: <span className="text-hata-text">{signature?.extension}</span></p>
              <p>Detected format: <span className="text-hata-text">{signature?.detected_format}</span></p>
              <p>{signature?.details}</p>
            </FindingCard>

            <FindingCard title="Hash Reputation" icon={Fingerprint}
              status={hashes?.virustotal_status === 'not_configured' ? 'not_detected' : (hashes?.virustotal_status === 'found' ? 'suspicious' : 'not_detected')}
              statusLabel={hashes?.virustotal_status === 'not_configured' ? 'Not Configured' : hashes?.virustotal_status}>
              <p className="mono break-all">SHA-256: {hashes?.sha256}</p>
              <p className="mono break-all">SHA-1: {hashes?.sha1}</p>
              <p className="mono break-all">MD5: {hashes?.md5}</p>
            </FindingCard>

            <FindingCard title="Metadata / EXIF" icon={Camera}
              status={metadata?.anomaly_detected ? 'suspicious' : 'safe'}
              statusLabel={metadata?.anomaly_detected ? 'Anomaly Found' : 'Normal'}>
              <p>Camera: {metadata?.camera_make || '—'} {metadata?.camera_model || ''}</p>
              <p>Software: {metadata?.software || '—'}</p>
              <p>Dimensions: {metadata?.width}×{metadata?.height}</p>
              <p>GPS present: {metadata?.gps_present ? 'Yes' : 'No'}</p>
              {metadata?.anomalies?.map((a, i) => <p key={i} className="text-risk-medium">⚠ {a.finding}</p>)}
            </FindingCard>

            <FindingCard title="Entropy Analysis" icon={Activity}
              status={entropy?.anomaly_detected ? 'suspicious' : 'safe'}
              statusLabel={entropy?.classification}>
              <p>Overall: {entropy?.overall_entropy} bits/byte</p>
              <p>Tail: {entropy?.tail_entropy} bits/byte</p>
              {entropy?.chunk_entropies?.length > 0 && (
                <div className="h-20 mt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={entropy.chunk_entropies}>
                      <XAxis dataKey="offset" hide />
                      <YAxis domain={[0, 8]} hide />
                      <Tooltip contentStyle={{ background: '#0b0f19', border: '1px solid #1c2333', fontSize: 11 }} />
                      <Line type="monotone" dataKey="entropy" stroke="#22d3ee" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
              <p className="italic">High entropy alone does not prove malicious content.</p>
            </FindingCard>

            <FindingCard title="Steganography" icon={EyeOff}
              status={stego?.classification === 'NOT DETECTED' ? 'safe' : (stego?.classification === 'HIGHLY SUSPICIOUS' ? 'dangerous' : 'suspicious')}
              statusLabel={stego?.classification}>
              <p>LSB score: {stego?.lsb_score ?? '—'}</p>
              <p>Chi-square: {stego?.chi_square_score ?? '—'}</p>
              <p className="italic">{stego?.notes}</p>
            </FindingCard>

            <FindingCard title="Embedded / Appended Data" icon={FileWarning}
              status={embedded?.embedded_signatures?.some(s => s.severity === 'CRITICAL') ? 'dangerous' :
                      (embedded?.appended_data_found || embedded?.embedded_signatures?.length > 0) ? 'suspicious' : 'safe'}
              statusLabel={embedded?.highest_severity === 'NONE' ? 'None' : embedded?.highest_severity}>
              <p>Appended data: {embedded?.appended_data_found ? `Yes (offset ${embedded.appended_data_offset}, ${embedded.appended_data_size} bytes)` : 'No'}</p>
              {embedded?.embedded_signatures?.map((s, i) => (
                <p key={i} className={s.severity === 'CRITICAL' ? 'text-risk-critical' : 'text-risk-medium'}>
                  {s.type} — offset {s.offset}, ~{(s.size / 1024).toFixed(1)} KB
                </p>
              ))}
            </FindingCard>

            <FindingCard title="YARA Scan" icon={ScanLine}
              status={!yara?.engine_available ? 'not_detected' : yara?.matches?.length > 0 ? 'dangerous' : 'safe'}
              statusLabel={!yara?.engine_available ? 'Unavailable' : `${yara?.matches?.length || 0} match(es)`}>
              <p>Rules scanned: {yara?.rules_scanned ?? 0}</p>
              {yara?.matches?.map((mch, i) => (
                <p key={i} className="text-risk-critical">{mch.rule} ({mch.severity}) — {mch.description}</p>
              ))}
            </FindingCard>

            <FindingCard title="OCR Analysis" icon={TextSearch}
              status={!ocr?.engine_available ? 'not_detected' : ocr?.suspicious_phrases?.length > 0 ? 'suspicious' : 'safe'}
              statusLabel={!ocr?.engine_available ? 'Unavailable' : (ocr?.suspicious_phrases?.length > 0 ? 'Phrases found' : 'Clean')}>
              {ocr?.engine_available ? (
                <>
                  <p>Suspicious phrases: {ocr?.suspicious_phrases?.join(', ') || 'None'}</p>
                  {ocr?.extracted_text && <p className="line-clamp-3 italic">"{ocr.extracted_text}"</p>}
                </>
              ) : <p>OCR analysis unavailable on this server.</p>}
            </FindingCard>

            <FindingCard title="QR Code Analysis" icon={QrCode}
              status={!qr?.engine_available ? 'not_detected' : qr?.qr_codes?.some(q => q.risk === 'HIGH') ? 'dangerous' : (qr?.qr_codes?.length > 0 ? 'suspicious' : 'safe')}
              statusLabel={!qr?.engine_available ? 'Unavailable' : `${qr?.qr_codes?.length || 0} found`}>
              {qr?.qr_codes?.map((q, i) => (
                <p key={i}>[{q.type}] {q.content.slice(0, 60)} — Risk: {q.risk}</p>
              ))}
              {qr?.engine_available && qr?.qr_codes?.length === 0 && <p>No QR codes detected.</p>}
            </FindingCard>

            <FindingCard title="URL Findings" icon={Globe2}
              status={url_results?.some(u => u.risk_level === 'HIGH') ? 'dangerous' : url_results?.length > 0 ? 'suspicious' : 'not_detected'}
              statusLabel={`${url_results?.length || 0} URL(s)`}>
              {url_results?.map((u, i) => (
                <p key={i}>{u.url.slice(0, 60)} — {u.risk_level} ({u.source})</p>
              ))}
              {(!url_results || url_results.length === 0) && <p>No URLs discovered via OCR or QR analysis.</p>}
            </FindingCard>
          </div>
        </>
      )}
    </div>
  )
}
