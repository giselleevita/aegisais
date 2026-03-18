/**
 * ITDAE-specific type definitions.
 * Extends types/index.ts with infrastructure threat detection types.
 */

export interface ItdaeAlert {
    id: number
    timestamp: string
    mmsi: string
    type: 'GEOFENCE_ENTRY' | 'LOITER_IN_ZONE' | 'AIS_DARK_IN_ZONE' | 'SLOW_TRANSIT_ZONE' | string
    severity: number
    summary: string
    status: string
    notes?: string | null
    evidence: ItdaeAlertEvidence
}

export interface ItdaeAlertEvidence {
    zone_id?: string
    zone_name?: string
    zone_risk_level?: 'critical' | 'high' | 'medium'
    lat?: number
    lon?: number
    timestamp?: string
    duration_min?: number
    gap_sec?: number
    implied_speed_kn?: number
    sog_kn?: number
    in_zone_before?: boolean
    in_zone_after?: boolean
    disappeared_at?: string
    reappeared_at?: string
    disappeared_lat?: number
    disappeared_lon?: number
    reappeared_lat?: number
    reappeared_lon?: number
    [key: string]: unknown
}

export interface ItdaeGeofenceZone {
    id: string
    name: string
    description: string
    risk_level: 'critical' | 'high' | 'medium'
    polygon: [number, number][]  // [lon, lat] pairs
}

export interface ItdaeHealthStatus {
    positions_today: number
    stream_status: 'running' | 'stopped'
}

export interface ItdaeVesselRisk {
    mmsi: string
    score: number
    label: 'critical' | 'high' | 'medium' | 'low'
    dominant_signal: string | null
    alert_count: number
}
