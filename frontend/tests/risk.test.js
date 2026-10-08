import { describe, it, expect } from 'vitest'
import { riskMeta, statusGlyph } from '../src/utils/risk.js'

describe('riskMeta', () => {
  it('returns correct metadata for known categories', () => {
    expect(riskMeta('SAFE').label).toBe('FILE SAFE')
    expect(riskMeta('CRITICAL').label).toBe('CRITICAL THREAT')
  })

  it('falls back to UNKNOWN for unrecognized categories', () => {
    expect(riskMeta('NOT_A_REAL_CATEGORY').label).toBe('UNKNOWN')
  })
})

describe('statusGlyph', () => {
  it('maps status values to glyphs', () => {
    expect(statusGlyph('safe')).toBe('✓')
    expect(statusGlyph('dangerous')).toBe('✕')
    expect(statusGlyph('suspicious')).toBe('⚠')
    expect(statusGlyph('not_detected')).toBe('—')
    expect(statusGlyph('unknown_value')).toBe('—')
  })
})
