import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Mail, ScanLine, History, ShieldAlert, FileText,
  Lock, BrainCircuit, Settings as SettingsIcon,
} from 'lucide-react'
import HataLogo from './HataLogo.jsx'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/automatic', label: 'Automatic Monitoring', icon: Mail },
  { to: '/scan', label: 'Manual Scan', icon: ScanLine },
  { to: '/history', label: 'Scan History', icon: History },
  { to: '/threat-intel', label: 'Threat Intelligence', icon: BrainCircuit },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/quarantine', label: 'Quarantine', icon: Lock },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
]

export default function Sidebar() {
  return (
    <aside className="hidden md:flex md:flex-col w-64 shrink-0 h-screen sticky top-0 border-r border-hata-border bg-hata-panel/60 backdrop-blur-md">
      <div className="px-5 py-5 border-b border-hata-border">
        <HataLogo />
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `focus-ring flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-hata-accent/10 text-hata-accent border border-hata-accent/30'
                  : 'text-hata-muted hover:text-hata-text hover:bg-white/5 border border-transparent'
              }`
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-hata-border text-[11px] text-hata-muted">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-risk-safe animate-pulseSlow" />
          System Operational
        </div>
        <div className="mt-1">Operation HATA v1.0.0</div>
      </div>
    </aside>
  )
}
