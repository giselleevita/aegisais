import { useEffect, useState } from 'react'
import { apiClient } from '../api/client'
import type { Alert } from '../api/client'
import './AlertsPanel.css'

export default function AlertsPanel() {
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [loading, setLoading] = useState(true)
    const [filterType, setFilterType] = useState<string>('')
    const [minSeverity, setMinSeverity] = useState(0)

    useEffect(() => {
        loadAlerts()
        const interval = setInterval(loadAlerts, 5000)
        return () => clearInterval(interval)
    }, [filterType, minSeverity])

    const loadAlerts = async () => {
        try {
            setLoading(true)
            const params: any = { limit: 100 }
            if (filterType) params.alert_type = filterType
            if (minSeverity > 0) params.min_severity = minSeverity
            const data = await apiClient.getAlerts(params)
            setAlerts(data)
        } catch (error) {
            console.error('Failed to load alerts:', error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="alerts-panel">
            <div className="panel-header">
                <div>
                    <h2>Alerts</h2>
                    <div className="panel-subtitle">
                        <span className="label">Integrity</span>: hard physics / data integrity violations.{" "}
                        <span className="label">Suspicious</span>: softer data‑quality or unusual behaviour signals.
                    </div>
                </div>
                <div className="panel-controls">
                    <select
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value)}
                        className="type-filter"
                    >
                        <option value="">All Types</option>
                        <option value="TELEPORT">Teleport (integrity)</option>
                        <option value="TELEPORT_T2">Teleport (suspicious)</option>
                        <option value="TURN_RATE">Turn rate (integrity)</option>
                        <option value="TURN_RATE_T2">Turn rate (suspicious)</option>
                        <option value="POSITION_INVALID">Position invalid</option>
                        <option value="ACCELERATION">Acceleration / SOG mismatch</option>
                        <option value="HEADING_COG_CONSISTENCY">Heading / COG consistency</option>
                    </select>
                    <select
                        value={minSeverity}
                        onChange={(e) => setMinSeverity(Number(e.target.value))}
                        className="severity-filter"
                    >
                        <option value={0}>All Severities</option>
                        <option value={30}>Low (30+)</option>
                        <option value={50}>Medium (50+)</option>
                        <option value={70}>High (70+)</option>
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="loading">Loading alerts...</div>
            ) : (
                <div className="alerts-list">
                    {alerts.length === 0 ? (
                        <div className="empty-state">No alerts found</div>
                    ) : (
                        alerts.map((alert) => (
                            <div key={alert.id} className={`alert-card severity-${getSeverityLevel(alert.severity)}`}>
                                <div className="alert-header">
                                    <div className="alert-type">
                                        {formatAlertType(alert.type)}
                                    </div>
                                    <div className={`severity-badge severity-${getSeverityLevel(alert.severity)}`}>
                                        {alert.severity}
                                    </div>
                                </div>
                                <div className="alert-summary">{alert.summary}</div>
                                <div className="alert-details">
                                    <div className="detail-item">
                                        <span className="label">MMSI:</span>
                                        <span>{alert.mmsi}</span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="label">Time:</span>
                                        <span>{new Date(alert.timestamp).toLocaleString()}</span>
                                    </div>
                                </div>
                                <div className="alert-details">
                                    <div className="detail-item">
                                        <span className="label">Class:</span>
                                        <span>{getAlertClassification(alert.type).tierLabel}</span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="label">Purpose:</span>
                                        <span>{getAlertClassification(alert.type).purpose}</span>
                                    </div>
                                </div>
                                {alert.evidence && (
                                    <details className="alert-evidence">
                                        <summary>Evidence</summary>
                                        {renderEvidence(alert)}
                                    </details>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}

function getSeverityLevel(severity: number): string {
    if (severity >= 70) return 'high'
    if (severity >= 30) return 'medium'
    return 'low'
}

function formatAlertType(type: string): string {
    switch (type) {
        case 'TELEPORT':
            return 'Teleport (integrity)'
        case 'TELEPORT_T2':
            return 'Teleport (suspicious)'
        case 'TURN_RATE':
            return 'Turn rate (integrity)'
        case 'TURN_RATE_T2':
            return 'Turn rate (suspicious)'
        case 'POSITION_INVALID':
            return 'Position invalid'
        case 'ACCELERATION':
            return 'Acceleration / SOG mismatch'
        case 'HEADING_COG_CONSISTENCY':
            return 'Heading / COG consistency'
        default:
            return type
    }
}

function getAlertClassification(type: string): { tier: 'integrity' | 'suspicious'; tierLabel: string; purpose: string } {
    switch (type) {
        case 'TELEPORT':
            return {
                tier: 'integrity',
                tierLabel: 'Integrity violation',
                purpose: 'Detects physically impossible position jumps (spoofing / gross data errors).',
            }
        case 'TURN_RATE':
            return {
                tier: 'integrity',
                tierLabel: 'Integrity violation',
                purpose: 'Detects impossible turn rates that ships cannot physically execute.',
            }
        case 'POSITION_INVALID':
            return {
                tier: 'integrity',
                tierLabel: 'Integrity violation',
                purpose: 'Catches clearly invalid positions (out of bounds, (0,0), or stuck while SOG says moving).',
            }
        case 'HEADING_COG_CONSISTENCY':
            return {
                tier: 'integrity',
                tierLabel: 'Integrity violation',
                purpose: 'Flags wild heading/COG changes at high speed that break basic kinematics.',
            }
        case 'TELEPORT_T2':
            return {
                tier: 'suspicious',
                tierLabel: 'Suspicious / data‑quality',
                purpose: 'Highlights medium‑speed jumps that are unusual but not full hard teleports.',
            }
        case 'TURN_RATE_T2':
            return {
                tier: 'suspicious',
                tierLabel: 'Suspicious / data‑quality',
                purpose: 'Surfaces moderate but unusual turns that may indicate track noise or manoeuvring.',
            }
        case 'ACCELERATION':
            return {
                tier: 'suspicious',
                tierLabel: 'Suspicious / data‑quality',
                purpose: 'Compares reported SOG vs track‑implied speed to find inconsistent / noisy data.',
            }
        default:
            return {
                tier: 'suspicious',
                tierLabel: 'Suspicious / data‑quality',
                purpose: 'Generic anomaly or data‑quality signal.',
            }
    }
}

function renderEvidence(alert: Alert) {
    const e: any = alert.evidence || {}

    switch (alert.type) {
        case 'TELEPORT':
        case 'TELEPORT_T2': {
            const dt = typeof e.dt_sec === 'number' ? e.dt_sec : undefined
            const distanceKm = typeof e.distance_m === 'number' ? e.distance_m / 1000 : undefined
            const speed = typeof e.implied_speed_kn === 'number' ? e.implied_speed_kn : undefined
            const tier = e.tier as string | undefined

            return (
                <ul className="evidence-list">
                    {dt !== undefined && (
                        <li>
                            <span className="label">Gap:</span> {formatSeconds(dt)}
                        </li>
                    )}
                    {distanceKm !== undefined && (
                        <li>
                            <span className="label">Distance:</span> {distanceKm.toFixed(1)} km
                        </li>
                    )}
                    {speed !== undefined && (
                        <li>
                            <span className="label">Implied speed:</span> {speed.toFixed(1)} kn
                        </li>
                    )}
                    {tier && (
                        <li>
                            <span className="label">Gap tier:</span> {formatTier(tier)}
                        </li>
                    )}
                </ul>
            )
        }
        case 'TURN_RATE':
        case 'TURN_RATE_T2': {
            const dt = typeof e.dt_sec === 'number' ? e.dt_sec : undefined
            const angle = typeof e.delta_angle_deg === 'number' ? e.delta_angle_deg : undefined
            const rate = typeof e.turn_rate_deg_s === 'number' ? e.turn_rate_deg_s : undefined
            const speed = typeof e.speed_kn === 'number' ? e.speed_kn : undefined
            const angleType = (e.angle_type as string | undefined) ?? 'heading / COG'
            const tier = e.tier as string | undefined

            return (
                <ul className="evidence-list">
                    {dt !== undefined && (
                        <li>
                            <span className="label">Window:</span> {formatSeconds(dt)}
                        </li>
                    )}
                    {angle !== undefined && (
                        <li>
                            <span className="label">Angle change:</span> {angle.toFixed(1)}°
                        </li>
                    )}
                    {rate !== undefined && (
                        <li>
                            <span className="label">Turn rate:</span> {rate.toFixed(2)}°/s
                        </li>
                    )}
                    {speed !== undefined && (
                        <li>
                            <span className="label">Speed:</span> {speed.toFixed(1)} kn
                        </li>
                    )}
                    <li>
                        <span className="label">Angle source:</span> {angleType}
                    </li>
                    {tier && (
                        <li>
                            <span className="label">Speed tier:</span> {formatTier(tier)}
                        </li>
                    )}
                </ul>
            )
        }
        case 'POSITION_INVALID': {
            const lat = e.lat
            const lon = e.lon
            const sog = e.sog
            const dt = typeof e.dt_sec === 'number' ? e.dt_sec : undefined

            return (
                <ul className="evidence-list">
                    {lat !== undefined && lon !== undefined && (
                        <li>
                            <span className="label">Position:</span> {lat.toFixed(4)}, {lon.toFixed(4)}
                        </li>
                    )}
                    {typeof sog === 'number' && (
                        <li>
                            <span className="label">Speed (SOG):</span> {sog.toFixed(1)} kn
                        </li>
                    )}
                    {dt !== undefined && (
                        <li>
                            <span className="label">Duration:</span> {formatSeconds(dt)}
                        </li>
                    )}
                </ul>
            )
        }
        case 'ACCELERATION': {
            const diff = typeof e.difference_kn === 'number' ? e.difference_kn : undefined
            const implied = typeof e.implied_speed_kn === 'number' ? e.implied_speed_kn : undefined
            const sogReported = typeof e.sog_reported === 'number' ? e.sog_reported : undefined
            const accel = typeof e.accel_knots_per_sec === 'number' ? e.accel_knots_per_sec : undefined

            return (
                <ul className="evidence-list">
                    {diff !== undefined && (
                        <li>
                            <span className="label">SOG vs track speed diff:</span> {diff.toFixed(1)} kn
                        </li>
                    )}
                    {sogReported !== undefined && (
                        <li>
                            <span className="label">Reported SOG:</span> {sogReported.toFixed(1)} kn
                        </li>
                    )}
                    {implied !== undefined && (
                        <li>
                            <span className="label">Implied speed:</span> {implied.toFixed(1)} kn
                        </li>
                    )}
                    {accel !== undefined && (
                        <li>
                            <span className="label">Acceleration:</span> {accel.toFixed(2)} kn/s
                        </li>
                    )}
                </ul>
            )
        }
        case 'HEADING_COG_CONSISTENCY': {
            const dt = typeof e.dt_sec === 'number' ? e.dt_sec : undefined
            const rate = typeof e.turn_rate_deg_s === 'number' ? e.turn_rate_deg_s : undefined
            const angle = typeof e.angle_change_deg === 'number' ? e.angle_change_deg : undefined
            const speed = typeof e.speed_kn === 'number' ? e.speed_kn : undefined
            const angleType = e.angle_type as string | undefined

            return (
                <ul className="evidence-list">
                    {dt !== undefined && (
                        <li>
                            <span className="label">Window:</span> {formatSeconds(dt)}
                        </li>
                    )}
                    {angle !== undefined && (
                        <li>
                            <span className="label">Angle change:</span> {angle.toFixed(1)}°
                        </li>
                    )}
                    {rate !== undefined && (
                        <li>
                            <span className="label">Turn rate:</span> {rate.toFixed(2)}°/s
                        </li>
                    )}
                    {speed !== undefined && (
                        <li>
                            <span className="label">Speed:</span> {speed.toFixed(1)} kn
                        </li>
                    )}
                    {angleType && (
                        <li>
                            <span className="label">Angle source:</span> {angleType}
                        </li>
                    )}
                </ul>
            )
        }
        default:
            // Fallback: show raw JSON if we don't have a nicer view yet
            return <pre>{JSON.stringify(e, null, 2)}</pre>
    }
}

function formatSeconds(sec: number): string {
    if (!Number.isFinite(sec) || sec < 0) return `${sec.toFixed(0)} s`
    if (sec < 90) return `${sec.toFixed(0)} s`
    const minutes = sec / 60
    if (minutes < 90) return `${minutes.toFixed(1)} min`
    const hours = minutes / 60
    return `${hours.toFixed(1)} h`
}

function formatTier(tier: string): string {
    switch (tier) {
        case 'short':
            return 'short gap'
        case 'medium':
            return 'medium gap'
        case 'long_gap':
            return 'long data gap'
        case 'low_speed':
            return 'low-speed turn'
        case 'normal':
            return 'normal-speed turn'
        case 'suspicious':
            return 'suspicious (Tier 2)'
        default:
            return tier
    }
}

