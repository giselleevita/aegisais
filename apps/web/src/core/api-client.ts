import { API_BASE_URL } from '@/core/config'
import { getAccessToken, setAccessToken } from '@/core/auth-token'
import type {
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
    LayerDefinition,
} from '@/shared/types/common'
import type { ItdaeGeofenceZone } from '@/features/itdae/types'

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
                let errorMessage = `API error: ${response.statusText}`
                try {
                    const errorData = await response.json()
                    errorMessage = errorData.detail || errorData.message || errorMessage
                } catch {
                    // If JSON parsing fails, use default message
                }
                throw new Error(errorMessage)
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

    /** Globe layer catalogue (analyst workbench). */
    async getLayers(): Promise<LayerDefinition[]> {
        return this.request<LayerDefinition[]>(`/v1/layers`)
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
        const response = await fetch(`${this.baseUrl}/v1/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body,
        })
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
}

export const apiClient = new ApiClient(API_BASE_URL)

