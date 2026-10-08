import React, { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Volume2, VolumeX, Shield, Play } from 'lucide-react'

// Web Audio API Synthesized Netflix 'TA-DUM' Chord
function playTaDumSound() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()

    const now = ctx.currentTime

    // 1. Initial hit ('TA') - short punchy low thump
    const osc1 = ctx.createOscillator()
    const gain1 = ctx.createGain()
    osc1.type = 'triangle'
    osc1.frequency.setValueAtTime(95, now)
    osc1.frequency.exponentialRampToValueAtTime(45, now + 0.18)

    gain1.gain.setValueAtTime(0.5, now)
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.22)

    osc1.connect(gain1)
    gain1.connect(ctx.destination)
    osc1.start(now)
    osc1.stop(now + 0.25)

    // 2. Main cinematic chord ('DUM') - delayed by ~0.16s
    const chordTime = now + 0.16
    const frequencies = [55, 73.42, 110, 164.81, 220, 329.63] // D minor / atmospheric cinematic chord

    frequencies.forEach((freq, idx) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc.type = idx % 2 === 0 ? 'sawtooth' : 'triangle'
      osc.frequency.setValueAtTime(freq * 0.99, chordTime)
      osc.frequency.linearRampToValueAtTime(freq, chordTime + 0.1)

      filter.type = 'lowpass'
      filter.frequency.setValueAtTime(1400, chordTime)
      filter.frequency.exponentialRampToValueAtTime(260, chordTime + 2.0)

      const volume = idx === 0 ? 0.35 : 0.18
      gain.gain.setValueAtTime(0.001, chordTime)
      gain.gain.linearRampToValueAtTime(volume, chordTime + 0.08)
      gain.gain.exponentialRampToValueAtTime(0.0001, chordTime + 2.4)

      osc.connect(filter)
      filter.connect(gain)
      gain.connect(ctx.destination)

      osc.start(chordTime)
      osc.stop(chordTime + 2.5)
    })
  } catch (err) {
    console.warn('Web Audio playback prevented by browser policy:', err)
  }
}

export default function NetflixIntro({ onComplete, autoStart = true }) {
  const [muted, setMuted] = useState(() => localStorage.getItem('hata_sound') === 'false')
  const [hasStarted, setHasStarted] = useState(autoStart)
  const soundPlayedRef = useRef(false)

  const triggerPlayback = () => {
    setHasStarted(true)
    if (!muted && !soundPlayedRef.current) {
      soundPlayedRef.current = true
      playTaDumSound()
    }
  }

  useEffect(() => {
    if (autoStart) {
      triggerPlayback()
    }
    const timer = setTimeout(() => {
      onComplete?.()
    }, 2800)
    return () => clearTimeout(timer)
  }, [autoStart, onComplete])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 1.08 }}
      transition={{ duration: 0.5, ease: 'easeInOut' }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#070707] text-white overflow-hidden select-none"
      onClick={() => {
        if (!soundPlayedRef.current && !muted) triggerPlayback()
      }}
    >
      {/* Background cinematic radial glows */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-red-600/20 blur-[130px] rounded-full animate-pulseSlow" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[250px] bg-cyan-500/15 blur-[100px] rounded-full" />
        {/* Cinematic horizontal ribbon flare */}
        <motion.div
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: [0, 1.8, 1], opacity: [0, 0.9, 0.4] }}
          transition={{ duration: 1.6, ease: 'easeOut' }}
          className="absolute top-1/2 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-red-600 to-transparent shadow-[0_0_20px_#e50914]"
        />
      </div>

      {/* Main Netflix Pop container */}
      <div className="relative z-10 flex flex-col items-center text-center px-6">
        {/* Animated Pop Shield Icon */}
        <motion.div
          initial={{ scale: 0.2, rotate: -30, opacity: 0 }}
          animate={{ scale: [0.2, 1.35, 1], rotate: [-30, 8, 0], opacity: 1 }}
          transition={{ duration: 0.9, times: [0, 0.65, 1], ease: [0.22, 1, 0.36, 1] }}
          className="mb-6 relative"
        >
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-red-600 via-red-700 to-black border-2 border-red-500/60 shadow-[0_0_50px_rgba(229,9,20,0.6)] flex items-center justify-center">
            <Shield className="w-10 h-10 text-white drop-shadow-[0_0_12px_rgba(255,255,255,0.8)]" strokeWidth={2.5} />
          </div>
          {/* Subtle pulse ring */}
          <motion.div
            initial={{ scale: 1, opacity: 0.8 }}
            animate={{ scale: 2.2, opacity: 0 }}
            transition={{ duration: 1.4, repeat: Infinity, ease: 'easeOut' }}
            className="absolute inset-0 rounded-2xl border-2 border-red-500/40 pointer-events-none"
          />
        </motion.div>

        {/* Netflix Pop Title: OPERATION HATA */}
        <motion.div
          initial={{ scale: 0.4, opacity: 0, letterSpacing: '0.1em' }}
          animate={{ scale: [0.4, 1.15, 1], opacity: 1, letterSpacing: ['0.1em', '0.35em', '0.25em'] }}
          transition={{ duration: 1.2, times: [0, 0.6, 1], ease: [0.16, 1, 0.3, 1] }}
          className="relative"
        >
          <h1
            className="text-4xl md:text-6xl lg:text-7xl font-black tracking-widest uppercase"
            style={{
              fontFamily: "'Inter', sans-serif",
              background: 'linear-gradient(180deg, #ffffff 15%, #e50914 85%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              filter: 'drop-shadow(0 0 35px rgba(229, 9, 20, 0.75))',
            }}
          >
            OPERATION HATA
          </h1>
        </motion.div>

        {/* Subtitle with reveal */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55, duration: 0.7, ease: 'easeOut' }}
          className="mt-4 flex items-center gap-3"
        >
          <div className="h-[1px] w-10 md:w-16 bg-red-600/60" />
          <span className="text-xs md:text-sm font-semibold tracking-[0.3em] uppercase text-zinc-300">
            Hidden Attachment Threat Analyzer
          </span>
          <div className="h-[1px] w-10 md:w-16 bg-red-600/60" />
        </motion.div>

        {/* Security SOC Status ticker */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 1, 0.7] }}
          transition={{ delay: 0.9, duration: 0.8 }}
          className="mt-8 flex items-center gap-2 text-[11px] tracking-wider uppercase text-zinc-400 bg-white/5 border border-white/10 px-4 py-1.5 rounded-full backdrop-blur-md"
        >
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span>CYBER FORENSICS SECURE WORKSTATION</span>
        </motion.div>
      </div>

      {/* Control bar: Sound toggle & Skip */}
      <div className="absolute bottom-8 left-8 right-8 flex items-center justify-between text-xs text-zinc-400 z-20">
        <button
          onClick={(e) => {
            e.stopPropagation()
            setMuted(!muted)
            localStorage.setItem('hata_sound', String(muted))
            if (muted && !soundPlayedRef.current) {
              soundPlayedRef.current = true
              playTaDumSound()
            }
          }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/10 hover:border-white/30 hover:text-white transition-colors bg-black/40 backdrop-blur-md"
          title="Toggle audio"
        >
          {muted ? <VolumeX className="w-4 h-4 text-zinc-400" /> : <Volume2 className="w-4 h-4 text-red-500" />}
          <span>{muted ? 'Sound Muted' : 'Ta-Dum Audio ON'}</span>
        </button>

        <button
          onClick={(e) => {
            e.stopPropagation()
            onComplete?.()
          }}
          className="flex items-center gap-2 px-4 py-1.5 rounded-lg border border-red-500/40 text-white font-medium hover:bg-red-600 hover:border-red-600 transition-all bg-red-950/30 backdrop-blur-md"
        >
          <span>Enter Console</span>
          <span className="text-[10px] text-zinc-400">Esc</span>
        </button>
      </div>
    </motion.div>
  )
}
