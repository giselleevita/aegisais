import { API_BASE_URL } from '../config'
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
} from '../types'

class ApiClient {
    private baseUrl: string

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl
    }

    private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options?.headers,
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

    async uploadFile(file: File): Promise<UploadResponse> {
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
}

export const apiClient = new ApiClient(API_BASE_URL)

