import { API_BASE_URL } from '@/core/config'
import { getAccessToken } from '@/core/auth-token'

/**
 * Builds ws/wss URL for `/v1/stream`. When signed in, appends the same JWT as the REST client
 * uses for `Authorization: Bearer` as `?token=` (WebSockets cannot send that header from the browser).
 */
export function getStreamWebSocketUrl(): string {
    const wsOrigin = API_BASE_URL.replace(/^https:\/\//, 'wss://').replace(/^http:\/\//, 'ws://')
    const base = wsOrigin.replace(/\/$/, '')
    const token = getAccessToken()
    if (!token) {
        return `${base}/v1/stream`
    }
    return `${base}/v1/stream?token=${encodeURIComponent(token)}`
}
