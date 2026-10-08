import { useEffect, useRef, useCallback, useState } from 'react'

export function useHataSocket(onMessage) {
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const handlerRef = useRef(onMessage)
  handlerRef.current = onMessage

  useEffect(() => {
    let cancelled = false
    let retryTimeout

    function connect() {
      let wsUrl = import.meta.env.VITE_WS_URL
      if (!wsUrl) {
        const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
        wsUrl = `${proto}://${window.location.host}/ws`
      }
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => { if (!cancelled) setConnected(true) }
      ws.onclose = () => {
        if (!cancelled) {
          setConnected(false)
          retryTimeout = setTimeout(connect, 3000)
        }
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          handlerRef.current?.(msg)
        } catch (e) { /* ignore malformed */ }
      }
    }
    connect()

    return () => {
      cancelled = true
      clearTimeout(retryTimeout)
      wsRef.current?.close()
    }
  }, [])

  return { connected }
}
