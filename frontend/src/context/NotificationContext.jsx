import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { listNotifications, markAllNotificationsRead } from '../services/api.js'
import { useHataSocket } from '../hooks/useHataSocket.js'

const NotificationContext = createContext(null)

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([])
  const [liveEvents, setLiveEvents] = useState([]) // scan_progress / dashboard_update pass-through
  const [socketConnected, setSocketConnected] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const data = await listNotifications()
      setNotifications(data)
    } catch (e) { /* backend may be offline momentarily */ }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const { connected } = useHataSocket((msg) => {
    if (msg.type === 'notification') {
      setNotifications((prev) => [{
        id: `live-${Date.now()}`,
        title: msg.data.title,
        message: msg.data.message,
        severity: msg.data.severity,
        read: false,
        created_at: new Date().toISOString(),
        scan_id: msg.data.scan_id,
      }, ...prev])
    }
    setLiveEvents((prev) => [msg, ...prev].slice(0, 50))
  })

  useEffect(() => { setSocketConnected(connected) }, [connected])

  const unreadCount = notifications.filter(n => !n.read).length

  const markAllRead = async () => {
    await markAllNotificationsRead().catch(() => {})
    setNotifications((prev) => prev.map(n => ({ ...n, read: true })))
  }

  return (
    <NotificationContext.Provider value={{
      notifications, unreadCount, refresh, markAllRead, liveEvents, socketConnected,
    }}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  return useContext(NotificationContext)
}
