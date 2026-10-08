/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        hata: {
          bg: 'rgb(var(--hata-bg) / <alpha-value>)',
          panel: 'rgb(var(--hata-panel) / <alpha-value>)',
          panel2: 'rgb(var(--hata-panel2) / <alpha-value>)',
          border: 'rgb(var(--hata-border) / <alpha-value>)',
          accent: 'rgb(var(--hata-accent) / <alpha-value>)',
          accent2: 'rgb(var(--hata-accent2) / <alpha-value>)',
          text: 'rgb(var(--hata-text) / <alpha-value>)',
          muted: 'rgb(var(--hata-muted) / <alpha-value>)',
        },
        risk: {
          safe: '#22c55e',
          low: '#38bdf8',
          medium: '#eab308',
          high: '#f97316',
          critical: '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 24px -4px rgba(var(--hata-glow), 0.35)',
        'glow-safe': '0 0 24px -4px rgba(34, 197, 94, 0.4)',
        'glow-critical': '0 0 24px -4px rgba(239, 68, 68, 0.45)',
      },
      keyframes: {
        pulseSlow: { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.6 } },
        scanline: { '0%': { backgroundPosition: '0 0' }, '100%': { backgroundPosition: '0 40px' } },
      },
      animation: {
        pulseSlow: 'pulseSlow 2.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
