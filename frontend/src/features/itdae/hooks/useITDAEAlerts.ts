import { useEffect, useRef, useState, useCallback } from 'react'
import type { ItdaeAlert } from '@/features/itdae/types'
import { API_BASE_URL } from '@/core/config'

const WS_URL = API_BASE_URL.replace(/^http/, 'ws') + '/v1/ws'
const ITDAE_TYPES = new Set([
    'GEOFENCE_ENTRY',
    'LOITER_IN_ZONE',
    'AIS_DARK_IN_ZONE',
    'SLOW_TRANSIT_ZONE',
])

interface UseITDAEAlertsReturn {
    alerts: ItdaeAlert[]
    connected: boolean
    unreadCount: number
    clearUnread: () => void
}

/**
 * useITDAEAlerts — extends the existing WebSocket connection to filter
 * and surface only ITDAE-specific alert events in real-time.
 *
 * Reuses the existing /v1/ws WebSocket endpoint; filters by alert type.
 * Keeps a sliding window of the last 50 ITDAE alerts in state.
 */
export function useITDAEAlerts(): UseITDAEAlertsReturn {
    const [alerts, setAlerts] = useState<ItdaeAlert[]>([])
    const [connected, setConnected] = useState(false)
    const [unreadCount, setUnreadCount] = useState(0)
    const wsRef = useRef<WebSocket | null>(null)
    const pingRef = useRef<number | null>(null)

    useEffect(() => {
        const ws = new WebSocket(WS_URL)
        wsRef.current = ws

        ws.onopen = () => {
            setConnected(true)
            pingRef.current = window.setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'ping' }))
                }
            }, 30000)
        }

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data)
                if (msg.kind === 'alert' && msg.data && ITDAE_TYPES.has(msg.data.type)) {
                    const itdaeAlert = msg.data as ItdaeAlert
                    setAlerts((prev) => [itdaeAlert, ...prev].slice(0, 50))
                    setUnreadCount((n) => n + 1)
                }
            } catch {
                // Ignore parse errors
            }
        }

        ws.onerror = () => setConnected(false)
        ws.onclose = () => {
            setConnected(false)
            if (pingRef.current) clearInterval(pingRef.current)
        }

        return () => {
            if (pingRef.current) clearInterval(pingRef.current)
            ws.close()
        }
    }, [])

    const clearUnread = useCallback(() => setUnreadCount(0), [])

    return { alerts, connected, unreadCount, clearUnread }
}
