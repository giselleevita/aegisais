import { API_BASE_URL } from '@/core/config'
import { getAccessToken, setAccessToken, setSessionUsername } from '@/core/auth-token'
import type {
    AuthContextResponse,
    Vessel,
    Alert,
    VesselPosition,
    ReplayStatus,
    AlertStats,
    AlertFilters,
    UploadedFile,
    UploadResponse,
    ReplayStartResponse,
    ReplayStopResponse,
    WatchlistEntry,
    IntegrationFeedsResponse,
    LayerManifestResponse,
    Incident,
    AuditLogEntry,
} from '@/shared/types/common'
import type { ItdaeGeofenceZone } from '@/features/itdae/types'

export class ApiClientError extends Error {
    status: number
    payload: Record<string, unknown> | null

    constructor(status: number, message: string, payload: Record<string, unknown> | null = null) {
        super(message)
        this.name = 'ApiClientError'
        this.status = status
        this.payload = payload
    }
}

function formatPolicyAwareError(
    status: number,
    errorData: Record<string, unknown> | null,
    fallbackMessage: string
): string {
    if (!errorData) return fallbackMessage

    const detail = typeof errorData.detail === 'string' ? errorData.detail : null
    const message = typeof errorData.message === 'string' ? errorData.message : null
    const error = typeof errorData.error === 'string' ? errorData.error : null
    const required = typeof errorData.required === 'string' ? errorData.required : null
    const effective = typeof errorData.effective === 'string' ? errorData.effective : null
    const feature = typeof errorData.feature === 'string' ? errorData.feature : null

    if (status === 403 && error === 'Insufficient classification clearance') {
        return required && effective
            ? `Access denied. ${required} clearance is required; current clearance is ${effective}.`
            : 'Access denied. Your clearance does not meet this route requirement.'
    }

    if (status === 403 && error === 'Insufficient releasability') {
        return required
            ? `Access denied. ${required} releasability is required for this route.`
            : 'Access denied. Your releasability tags do not satisfy this route.'
    }

    if (status === 403 && error === 'License required') {
        return feature
            ? `Access denied. ${feature} entitlement is required for this feature.`
            : 'Access denied. Your current license does not cover this feature.'
    }

    return detail || message || error || fallbackMessage
}

class ApiClient {
    private baseUrl: string

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl
    }

    private authHeaders(): Record<string, string> {
        const t = getAccessToken()
        return t ? { Authorization: `Bearer ${t}` } : {}
    }

    private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...this.authHeaders(),
                    ...(options?.headers as Record<string, string> | undefined),
                },
            })

            if (!response.ok) {
                if (response.status === 401 && getAccessToken()) {
                    setAccessToken(null)
                    throw new Error('Session expired or access denied. Sign in again.')
                }
                let errorMessage = `API error: ${response.statusText}`
                let errorData: Record<string, unknown> | null = null
                try {
                    errorData = (await response.json()) as Record<string, unknown>
                    errorMessage = formatPolicyAwareError(response.status, errorData, errorMessage)
                } catch {
                    // If JSON parsing fails, use default message
                }
                throw new ApiClientError(response.status, errorMessage, errorData)
            }

            return response.json() as Promise<T>
        } catch (error) {
            if (error instanceof Error) {
                throw error
            }
            throw new Error('Unknown error occurred')
        }
    }

    async getVessels(minSeverity = 0, limit = 500): Promise<Vessel[]> {
        return this.request<Vessel[]>(`/v1/vessels?min_severity=${minSeverity}&limit=${limit}`)
    }

    async getVessel(mmsi: string): Promise<Vessel> {
        return this.request<Vessel>(`/v1/vessels/${mmsi}`)
    }

    async getAlerts(params: AlertFilters = {}): Promise<Alert[]> {
        const queryParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                queryParams.append(key, value.toString())
            }
        })
        const query = queryParams.toString()
        return this.request<Alert[]>(`/v1/alerts${query ? `?${query}` : ''}`)
    }

    async getAlert(id: number): Promise<Alert> {
        return this.request<Alert>(`/v1/alerts/${id}`)
    }

    async getAlertStats(params: {
        start_time?: string
        end_time?: string
    } = {}): Promise<AlertStats> {
        const queryParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                queryParams.append(key, value.toString())
            }
        })
        const query = queryParams.toString()
        return this.request(`/v1/alerts/stats/summary${query ? `?${query}` : ''}`)
    }

    async startReplay(
        path: string,
        speedup = 100.0,
        useStreaming = true,
        batchSize = 100
    ): Promise<ReplayStartResponse> {
        const params = new URLSearchParams({
            path,
            speedup: speedup.toString(),
            use_streaming: useStreaming.toString(),
            batch_size: batchSize.toString(),
        })
        return this.request(`/v1/replay/start?${params.toString()}`, {
            method: 'POST',
        })
    }

    async stopReplay(): Promise<ReplayStopResponse> {
        return this.request(`/v1/replay/stop`, {
            method: 'POST',
        })
    }

    async getReplayStatus(): Promise<ReplayStatus> {
        return this.request<ReplayStatus>(`/v1/replay/status`)
    }

    /** Optional feed integrations (S-AIS, SAR, RF); requires authenticated viewer+. */
    async getIntegrationFeeds(): Promise<IntegrationFeedsResponse> {
        return this.request<IntegrationFeedsResponse>(`/v1/integrations/feeds`)
    }

    /** Authoritative frontend auth context from the BFF policy surface. */
    async getAuthContext(): Promise<AuthContextResponse> {
        return this.request<AuthContextResponse>(`/v1/auth/context`)
    }

    /** Globe layer catalogue manifest (analyst workbench). */
    async getLayersManifest(): Promise<LayerManifestResponse> {
        return this.request<LayerManifestResponse>(`/v1/layers/manifest`)
    }

    async uploadFile(file: File): Promise<UploadResponse> {
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch(`${this.baseUrl}/v1/upload`, {
            method: 'POST',
            body: formData,
            headers: this.authHeaders(),
        })

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }))
            throw new Error(error.detail || `Upload failed: ${response.statusText}`)
        }

        return response.json()
    }

    async listUploadedFiles(): Promise<{ files: UploadedFile[] }> {
        return this.request<{ files: UploadedFile[] }>(`/v1/upload/list`)
    }

    async updateAlertStatus(alertId: number, status: string, notes?: string): Promise<Alert> {
        return this.request<Alert>(`/v1/alerts/${alertId}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ status, notes }),
        })
    }

    async getVesselTrack(
        mmsi: string,
        startTime?: string,
        endTime?: string,
        limit = 1000
    ): Promise<VesselPosition[]> {
        const params = new URLSearchParams({ limit: limit.toString() })
        if (startTime) params.append('start_time', startTime)
        if (endTime) params.append('end_time', endTime)
        return this.request<VesselPosition[]>(`/v1/vessels/${mmsi}/track?${params.toString()}`)
    }

    /**
     * Legacy URL for unauthenticated download attempts (will 401 when exports require admin).
     * Prefer {@link downloadAlertsExport}.
     */
    exportAlerts(format: 'csv' | 'json', params: AlertFilters = {}): string {
        const queryParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                queryParams.append(key, value.toString())
            }
        })
        const query = queryParams.toString()
        return `${this.baseUrl}/v1/alerts/export/${format}${query ? `?${query}` : ''}`
    }

    /**
     * Download export with Bearer token (required when API enforces auth on export routes).
     */
    async downloadAlertsExport(format: 'csv' | 'json', params: AlertFilters = {}): Promise<void> {
        const queryParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                queryParams.append(key, value.toString())
            }
        })
        const query = queryParams.toString()
        const url = `${this.baseUrl}/v1/alerts/export/${format}${query ? `?${query}` : ''}`
        const response = await fetch(url, { headers: this.authHeaders() })
        if (!response.ok) {
            let message = `Export failed: ${response.statusText}`
            try {
                const err = await response.json()
                message = err.detail || message
            } catch {
                /* ignore */
            }
            throw new Error(message)
        }
        const blob = await response.blob()
        const cd = response.headers.get('Content-Disposition')
        let filename = `alerts_export.${format}`
        const m = cd?.match(/filename="?([^";]+)"?/i)
        if (m?.[1]) filename = m[1].trim()
        const objectUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = objectUrl
        a.download = filename
        a.click()
        URL.revokeObjectURL(objectUrl)
    }

    async login(username: string, password: string): Promise<{ access_token: string; token_type: string }> {
        const body = new URLSearchParams()
        body.set('username', username)
        body.set('password', password)
        let response: Response
        try {
            response = await fetch(`${this.baseUrl}/v1/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body,
            })
        } catch {
            throw new Error('Cannot reach the API policy surface. Check the server is running and VITE_API_BASE_URL.')
        }
        if (!response.ok) {
            let message = 'Login failed'
            try {
                const err = await response.json()
                message = err.detail || message
            } catch {
                /* ignore */
            }
            throw new Error(message)
        }
        const data = (await response.json()) as { access_token: string; token_type: string }
        // Username before token so AUTH_CHANGED listeners see both together.
        setSessionUsername(username.trim())
        setAccessToken(data.access_token)
        return data
    }

    logout(): void {
        setAccessToken(null)
    }

    /** ITDAE routes live under `/api/v1/itdae` (not `/v1`). Requires Bearer auth when enforced server-side. */
    async getItdaeBalticGeofences(): Promise<{ count: number; zones: ItdaeGeofenceZone[] }> {
        return this.request<{ count: number; zones: ItdaeGeofenceZone[] }>(
            `/api/v1/itdae/geofences/baltic`
        )
    }

    async getWatchlist(): Promise<WatchlistEntry[]> {
        return this.request<WatchlistEntry[]>(`/v1/watchlist`)
    }

    async getIncidents(params: { status?: string; limit?: number; offset?: number } = {}): Promise<Incident[]> {
        const queryParams = new URLSearchParams()
        if (params.status) queryParams.append('status', params.status)
        if (params.limit !== undefined) queryParams.append('limit', String(params.limit))
        if (params.offset !== undefined) queryParams.append('offset', String(params.offset))
        const query = queryParams.toString()
        return this.request<Incident[]>(`/v1/incidents${query ? `?${query}` : ''}`)
    }

    async getIncident(id: number): Promise<Incident> {
        return this.request<Incident>(`/v1/incidents/${id}`)
    }

    async updateIncident(id: number, payload: { status?: string; title?: string }): Promise<Incident> {
        return this.request<Incident>(`/v1/incidents/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(payload),
        })
    }

    async getAuditLogs(params: {
        action?: string
        user_id?: string
        resource_id?: string
        resource_type?: string
        start_time?: string
        end_time?: string
        limit?: number
        offset?: number
    } = {}): Promise<AuditLogEntry[]> {
        const q = new URLSearchParams()
        Object.entries(params).forEach(([k, v]) => {
            if (v !== undefined && v !== null && v !== '') q.append(k, String(v))
        })
        const query = q.toString()
        return this.request<AuditLogEntry[]>(`/v1/audit/logs${query ? `?${query}` : ''}`)
    }

    async downloadAuditLogsCsv(params: {
        action?: string
        user_id?: string
        resource_id?: string
        resource_type?: string
        start_time?: string
        end_time?: string
        max_rows?: number
    } = {}): Promise<void> {
        const q = new URLSearchParams()
        Object.entries(params).forEach(([k, v]) => {
            if (v !== undefined && v !== null && v !== '') q.append(k, String(v))
        })
        const query = q.toString()
        const url = `${this.baseUrl}/v1/audit/logs/export/csv${query ? `?${query}` : ''}`
        const response = await fetch(url, { headers: this.authHeaders() })
        if (!response.ok) {
            let message = `Export failed: ${response.statusText}`
            try {
                const err = await response.json()
                message = err.detail || message
            } catch {
                /* ignore */
            }
            throw new Error(message)
        }
        const blob = await response.blob()
        const cd = response.headers.get('Content-Disposition')
        let filename = 'audit_logs_export.csv'
        const m = cd?.match(/filename="?([^";]+)"?/i)
        if (m?.[1]) filename = m[1].trim()
        const objectUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = objectUrl
        a.download = filename
        a.click()
        URL.revokeObjectURL(objectUrl)
    }

    async addWatchlistEntry(payload: {
        mmsi: string
        label?: string
        priority?: 'low' | 'medium' | 'high'
    }): Promise<WatchlistEntry> {
        return this.request<WatchlistEntry>(`/v1/watchlist`, {
            method: 'POST',
            body: JSON.stringify({
                label: payload.label ?? '',
                priority: payload.priority ?? 'medium',
                mmsi: payload.mmsi,
            }),
        })
    }

    async removeWatchlistEntry(mmsi: string): Promise<void> {
        const response = await fetch(
            `${this.baseUrl}/v1/watchlist/${encodeURIComponent(mmsi)}`,
            {
                method: 'DELETE',
                headers: this.authHeaders(),
            }
        )
        if (!response.ok) {
            let errorMessage = `API error: ${response.statusText}`
            try {
                const errorData = await response.json()
                errorMessage = errorData.detail || errorData.message || errorMessage
            } catch {
                /* ignore */
            }
            throw new Error(errorMessage)
        }
    }

    // ── Geodata / Environmental Context ──────────────────────────

    async getEezZones(): Promise<{
        count: number
        zones: Array<{
            name: string
            sovereign: string
            iso3: string
            mrgid?: number
            bbox?: [number, number, number, number]
        }>
    }> {
        return this.request(`/v1/geodata/eez/zones`)
    }

    async identifyEez(lat: number, lon: number): Promise<{
        lat: number
        lon: number
        eez: { name: string; sovereign: string; iso3: string } | null
        international_waters: boolean
    }> {
        return this.request(`/v1/geodata/eez/identify?lat=${lat}&lon=${lon}`)
    }

    async getEnvironmentalContext(lat: number, lon: number): Promise<{
        position: { lat: number; lon: number }
        eez: { name: string; sovereign: string; iso3: string } | null
        international_waters: boolean
        weather: {
            wave_height_m?: number
            wind_speed_kmh?: number
            sea_state?: string
            sea_state_description?: string
        } | null
        depth: {
            depth_m?: number
            depth_category?: string
            is_land?: boolean
        } | null
    }> {
        return this.request(`/v1/geodata/context?lat=${lat}&lon=${lon}`)
    }

    async getWeather(lat: number, lon: number): Promise<{
        lat: number
        lon: number
        available: boolean
        weather: Record<string, unknown> | null
    }> {
        return this.request(`/v1/geodata/weather?lat=${lat}&lon=${lon}`)
    }

    async getBathymetry(lat: number, lon: number): Promise<{
        lat: number
        lon: number
        available: boolean
        depth: Record<string, unknown> | null
    }> {
        return this.request(`/v1/geodata/bathymetry?lat=${lat}&lon=${lon}`)
    }

    // ── Sanctions ────────────────────────────────────────────────

    async syncSanctionsWatchlist(): Promise<{
        status: string
        source: string
        mmsi_count: number
        imo_count: number
        name_count: number
    }> {
        return this.request(`/v1/sanctions/watchlist/sync`, { method: 'POST' })
    }
}

export const apiClient = new ApiClient(API_BASE_URL)

