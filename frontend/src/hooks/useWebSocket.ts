import { useEffect, useRef, useState } from 'react'
import type { WebSocketMessage } from '../types'

interface UseWebSocketReturn {
  connected: boolean
  lastMessage: WebSocketMessage | null
  sendMessage: (message: string) => void
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const [connected, setConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pingIntervalRef = useRef<number | null>(null)

  useEffect(() => {
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      // Send a ping to keep connection alive
      pingIntervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        } else {
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current)
            pingIntervalRef.current = null
          }
        }
      }, 30000) // Ping every 30 seconds
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage
        setLastMessage(data)
      } catch (e) {
        // Silently handle parse errors - invalid messages are ignored
        // In production, consider logging to monitoring service
        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console
          console.warn('Failed to parse WebSocket message:', e)
        }
      }
    }

    ws.onerror = () => {
      setConnected(false)
      // Error details are logged by browser, no need to duplicate
    }

    ws.onclose = () => {
      setConnected(false)
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = null
      }
    }

    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
      }
      ws.close()
    }
  }, [url])

  const sendMessage = (message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message)
    }
  }

  return { connected, lastMessage, sendMessage }
}


