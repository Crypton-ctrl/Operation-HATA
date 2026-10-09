import React, { useState, useEffect, useCallback } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from './components/layout/Sidebar.jsx'
import TopNav from './components/layout/TopNav.jsx'
import Login from './pages/Login.jsx'

import { NotificationProvider } from './context/NotificationContext.jsx'
import { ThemeProvider, useTheme } from './context/ThemeContext.jsx'
import { AuthProvider, useAuth } from './context/AuthContext.jsx'

import Dashboard from './pages/Dashboard.jsx'
import AutomaticMonitoring from './pages/AutomaticMonitoring.jsx'
import ManualScan from './pages/ManualScan.jsx'
import ScanResult from './pages/ScanResult.jsx'
import History from './pages/History.jsx'
import Reports from './pages/Reports.jsx'
import Quarantine from './pages/Quarantine.jsx'
import ThreatIntelligence from './pages/ThreatIntelligence.jsx'
import Settings from './pages/Settings.jsx'

const PAGE_META = {
  '/': { title: 'Security Dashboard', subtitle: 'AI-Powered Attachment Security Overview' },
  '/automatic': { title: 'Automatic Monitoring', subtitle: 'Gmail attachment monitoring & sync' },
  '/scan': { title: 'Manual Scan', subtitle: 'Upload and analyze an image independently' },
  '/history': { title: 'Scan History', subtitle: 'Searchable record of every analyzed attachment' },
  '/threat-intel': { title: 'Threat Intelligence', subtitle: 'Patterns across historical scan data' },
  '/reports': { title: 'Reports', subtitle: 'AI-generated security reports' },
  '/quarantine': { title: 'Quarantine', subtitle: 'Isolated suspicious and dangerous attachments' },
  '/settings': { title: 'Settings', subtitle: 'Email, AI, scanner, and notification configuration' },
}

function PageTransition({ children }) {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

function Shell({ children, title, subtitle, onLogout }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 min-w-0">
        <TopNav title={title} subtitle={subtitle} onLogout={onLogout} />
        <main className="p-4 md:p-8 max-w-[1600px] mx-auto">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
    </div>
  )
}

function AppContent() {
  const { isAuthenticated, logout } = useAuth()

  return (
    <>
      {!isAuthenticated ? (
        <Login onSuccess={() => {}} />
      ) : (
        <NotificationProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Shell {...PAGE_META['/']} onLogout={logout}><Dashboard /></Shell>} />
              <Route path="/automatic" element={<Shell {...PAGE_META['/automatic']} onLogout={logout}><AutomaticMonitoring /></Shell>} />
              <Route path="/scan" element={<Shell {...PAGE_META['/scan']} onLogout={logout}><ManualScan /></Shell>} />
              <Route path="/scan-result/:scanId" element={<Shell title="Scan Result" subtitle="Detailed attachment security analysis" onLogout={logout}><ScanResult /></Shell>} />
              <Route path="/history" element={<Shell {...PAGE_META['/history']} onLogout={logout}><History /></Shell>} />
              <Route path="/threat-intel" element={<Shell {...PAGE_META['/threat-intel']} onLogout={logout}><ThreatIntelligence /></Shell>} />
              <Route path="/reports" element={<Shell {...PAGE_META['/reports']} onLogout={logout}><Reports /></Shell>} />
              <Route path="/quarantine" element={<Shell {...PAGE_META['/quarantine']} onLogout={logout}><Quarantine /></Shell>} />
              <Route path="/settings" element={<Shell {...PAGE_META['/settings']} onLogout={logout}><Settings /></Shell>} />
            </Routes>
          </BrowserRouter>
        </NotificationProvider>
      )}
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <AppContent />
      </ThemeProvider>
    </AuthProvider>
  )
}
