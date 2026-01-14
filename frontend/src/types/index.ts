/**
 * Type definitions for AegisAIS frontend
 */

export interface AlertEvidence {
    dt_sec?: number
    distance_m?: number
    implied_speed_kn?: number
    turn_rate_deg_per_sec?: number
    accel_knots_per_sec?: number
    tier?: string
    p1_lat?: number
    p1_lon?: number
    p1_timestamp?: string
    p2_lat?: number
    p2_lon?: number
    p2_timestamp?: string
    p2_sog?: number | null
    p2_cog?: number | null
    p2_heading?: number | null
    reason?: string
    sog_diff?: number
    implied_speed?: number
    heading_delta?: number
    cog_delta?: number
    [key: string]: unknown // Allow additional fields
}

export interface Alert {
    id: number
    timestamp: string
    mmsi: string
    type: string
    severity: number
    summary: string
    evidence: AlertEvidence
    status?: string
    notes?: string | null
}

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

export interface VesselPosition {
    id: number
    mmsi: string
    timestamp: string
    lat: number
    lon: number
    sog: number | null
    cog: number | null
    heading: number | null
}

export interface ReplayStatus {
    running: boolean
    processed: number
    last_timestamp: string | null
    stop_requested: boolean
}

export interface AlertStats {
    total: number
    by_type: Record<string, number>
    average_severity: number
    by_severity_range: {
        high: number
        medium: number
        low: number
    }
}

export interface WebSocketMessage {
    kind: 'alert' | 'tick' | 'error'
    data?: Alert
    processed?: number
    message?: string
}

export interface AlertFilters {
    mmsi?: string
    alert_type?: string
    status?: string
    min_severity?: number
    max_severity?: number
    start_time?: string
    end_time?: string
    limit?: number
    offset?: number
}

export interface UploadedFile {
    filename: string
    path: string
    size_bytes: number
    size_mb: number
}

export interface UploadResponse {
    status: string
    filename: string
    path: string
    size_bytes: number
    size_mb: number
}

export interface ReplayStartResponse {
    status: string
    path: string
    speedup: number
    streaming: boolean
    batch_size: number
}

export interface ReplayStopResponse {
    status: string
}
