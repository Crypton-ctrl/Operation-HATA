import { ShieldCheck, ShieldAlert, ShieldQuestion, ShieldX, ShieldMinus } from 'lucide-react'

export const RISK_META = {
  SAFE: { color: '#22c55e', bg: 'bg-risk-safe', text: 'text-risk-safe', border: 'border-risk-safe',
          label: 'FILE SAFE', icon: ShieldCheck, glow: 'shadow-glow-safe' },
  LOW: { color: '#38bdf8', bg: 'bg-risk-low', text: 'text-risk-low', border: 'border-risk-low',
         label: 'LOW RISK', icon: ShieldQuestion, glow: 'shadow-glow' },
  MEDIUM: { color: '#eab308', bg: 'bg-risk-medium', text: 'text-risk-medium', border: 'border-risk-medium',
            label: 'MEDIUM RISK', icon: ShieldAlert, glow: 'shadow-glow' },
  HIGH: { color: '#f97316', bg: 'bg-risk-high', text: 'text-risk-high', border: 'border-risk-high',
          label: 'HIGH RISK', icon: ShieldAlert, glow: 'shadow-glow-critical' },
  CRITICAL: { color: '#ef4444', bg: 'bg-risk-critical', text: 'text-risk-critical', border: 'border-risk-critical',
              label: 'CRITICAL THREAT', icon: ShieldX, glow: 'shadow-glow-critical' },
  UNKNOWN: { color: '#7c8aa5', bg: 'bg-hata-muted', text: 'text-hata-muted', border: 'border-hata-muted',
             label: 'UNKNOWN', icon: ShieldMinus, glow: '' },
}

export function riskMeta(category) {
  return RISK_META[category] || RISK_META.UNKNOWN
}

export function statusGlyph(value) {
  // for card status: 'safe' | 'suspicious' | 'dangerous' | 'not_detected'
  const map = {
    safe: '✓', suspicious: '⚠', dangerous: '✕', not_detected: '—',
  }
  return map[value] || '—'
}
