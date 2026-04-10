import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import type { ItdaeAlert } from '@/features/itdae/types'
import { getStreamWebSocketUrl } from '@/core/ws-url'
import { evaluatePolicyRequirements, useAuthoritativeAuthContext } from '@/core/auth-context'
import { getAccessToken } from '@/core/auth-token'
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
 * useITDAEAlerts — subscribes to the shared /v1/stream WebSocket and filters
 * ITDAE-specific alert events (same transport as useWebSocket).
 */
export function useITDAEAlerts(): UseITDAEAlertsReturn {
    const { context: authContext, loading: authContextLoading } = useAuthoritativeAuthContext()
    const hasSession = !!getAccessToken()
    const streamAccess = useMemo(
        () =>
            evaluatePolicyRequirements(
                authContext,
                {
                    minClearance: 'CONFIDENTIAL',
                    requiredReleasability: ['NATO'],
                    requiredLicenses: ['ports:read'],
                },
                {
                    loading: authContextLoading,
                    hasSession,
                    fallbackLabel: 'ITDAE alerts',
                }
            ),
        [authContext, authContextLoading, hasSession]
    )
    const [alerts, setAlerts] = useState<ItdaeAlert[]>([])
    const [connected, setConnected] = useState(false)
    const [unreadCount, setUnreadCount] = useState(0)
    const wsRef = useRef<WebSocket | null>(null)
    const pingRef = useRef<number | null>(null)
    const streamUrl = streamAccess.allowed ? getStreamWebSocketUrl() : null

    useEffect(() => {
        if (!streamUrl) {
            return
        }

        const ws = new WebSocket(streamUrl)
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
            pingRef.current = null
            wsRef.current = null
            ws.close()
        }
    }, [streamUrl])

    const clearUnread = useCallback(() => setUnreadCount(0), [])

    return { alerts, connected: streamUrl ? connected : false, unreadCount, clearUnread }
}
