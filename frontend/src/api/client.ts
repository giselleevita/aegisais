import { API_BASE_URL } from '../config'

export interface Vessel {
    mmsi: string
    timestamp: string
    lat: number
    lon: number
    sog: number | null
    cog: number | null
    heading: number | null
    last_alert_severity: number
}

export interface Alert {
    id: number
    timestamp: string
    mmsi: string
    type: string
    severity: number
    summary: string
    evidence: any
}

export interface ReplayStatus {
    running: boolean
    processed: number
    last_timestamp: string | null
    stop_requested: boolean
}

class ApiClient {
    private baseUrl: string

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl
    }

    private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options?.headers,
            },
        })

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`)
        }

        return response.json()
    }

    async getVessels(minSeverity = 0, limit = 500): Promise<Vessel[]> {
        return this.request<Vessel[]>(`/v1/vessels?min_severity=${minSeverity}&limit=${limit}`)
    }

    async getVessel(mmsi: string): Promise<Vessel> {
        return this.request<Vessel>(`/v1/vessels/${mmsi}`)
    }

    async getAlerts(params: {
        mmsi?: string
        alert_type?: string
        min_severity?: number
        max_severity?: number
        start_time?: string
        end_time?: string
        limit?: number
        offset?: number
    } = {}): Promise<Alert[]> {
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
    } = {}): Promise<any> {
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
    ): Promise<{ status: string; path: string; speedup: number; streaming: boolean; batch_size: number }> {
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

    async stopReplay(): Promise<{ status: string }> {
        return this.request(`/v1/replay/stop`, {
            method: 'POST',
        })
    }

    async getReplayStatus(): Promise<ReplayStatus> {
        return this.request<ReplayStatus>(`/v1/replay/status`)
    }

    async uploadFile(file: File): Promise<{ status: string; filename: string; path: string; size_bytes: number; size_mb: number }> {
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch(`${this.baseUrl}/v1/upload`, {
            method: 'POST',
            body: formData,
            // Don't set Content-Type header - browser will set it with boundary for FormData
        })

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }))
            throw new Error(error.detail || `Upload failed: ${response.statusText}`)
        }

        return response.json()
    }

    async listUploadedFiles(): Promise<{ files: Array<{ filename: string; path: string; size_bytes: number; size_mb: number }> }> {
        return this.request(`/v1/upload/list`)
    }
}

export const apiClient = new ApiClient(API_BASE_URL)

