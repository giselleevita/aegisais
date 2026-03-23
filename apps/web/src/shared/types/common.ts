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
    /** Set when the vessel MMSI is on the analyst watchlist (alert pipeline). */
    watchlist_priority?: 'low' | 'medium' | 'high'
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

/**
 * Real-time payloads from `/v1/stream` (legacy `kind` events + typed status updates).
 * Single struct keeps dashboard/replay code simple; not every field applies to every message.
 */
export interface WebSocketMessage {
    kind?: 'alert' | 'tick' | 'error'
    type?: 'alert_status_updated'
    data?: Alert
    processed?: number
    message?: string
    alert_id?: number
    status?: string
    updated_by?: string
    timestamp?: string
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

export interface WatchlistEntry {
    id: number
    mmsi: string
    label: string
    priority: 'low' | 'medium' | 'high'
    added_by_id: number
    created_at: string
    is_active: boolean
}

/** GET /v1/integrations/feeds — optional external sensor feeds (AML admin UI). */
export type IntegrationFeedStatus = 'ready' | 'partial' | 'disconnected' | 'error'

export interface IntegrationFeed {
    id: string
    label: string
    status: IntegrationFeedStatus
    detail: string | null
}

export interface IntegrationFeedsResponse {
    timestamp: string
    feeds: IntegrationFeed[]
}

export interface Incident {
    id: number
    organisation_id: number
    alert_id: number
    created_at: string
    status: string
    title: string
    evidence_bundle: Record<string, unknown>
}

export interface LayerMetadata {
    provenance: string
    confidence: number
    source: string
    access: string
    licence: string
}

export interface LayerDefinition {
    id: string
    name: string
    description?: string
    category: 'live' | 'reference' | 'infrastructure' | 'intel'
    enabledByDefault?: boolean
    restricted?: boolean
    nonCommercial?: boolean
    metadata: LayerMetadata
}

export interface AuditLogEntry {
    id: number
    organisation_id: number
    timestamp: string
    user_id: string | null
    action: string
    resource_id: string | null
    resource_type: string | null
    change_summary: string
    details: Record<string, unknown> | null
    correlation_id: string | null
}
