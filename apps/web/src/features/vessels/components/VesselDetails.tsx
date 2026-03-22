import { useEffect, useState } from 'react'
import { apiClient } from '@/core/api-client'
import type { Vessel, Alert, VesselPosition } from '@/shared/types/common'
import { getSeverityLevel } from '@/features/alerts/lib/alertEvidence'
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import type { LatLngExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import '@/shared/map/leafletSetup'
import MapBounds from '@/shared/map/MapBounds'
import { createAlertDivIcon, createVesselDivIcon } from '@/shared/map/alertMarkers'
import './VesselDetails.css'

interface VesselDetailsProps {
    mmsi: string
    onClose: () => void
}

export default function VesselDetails({ mmsi, onClose }: VesselDetailsProps) {
    const [vessel, setVessel] = useState<Vessel | null>(null)
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [track, setTrack] = useState<VesselPosition[]>([])
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState<'overview' | 'alerts' | 'track'>('overview')
    const [onWatchlist, setOnWatchlist] = useState(false)
    const [wlLabel, setWlLabel] = useState('')
    const [wlPriority, setWlPriority] = useState<'low' | 'medium' | 'high'>('medium')

    useEffect(() => {
        if (mmsi) {
            loadVesselData()
            const interval = setInterval(loadVesselData, 10000)
            return () => clearInterval(interval)
        }
    }, [mmsi])

    const loadVesselData = async () => {
        if (!mmsi) return
        
        try {
            setLoading(true)
            const [vesselData, alertsData, trackData, watchlistData] = await Promise.all([
                apiClient.getVessel(mmsi),
                apiClient.getAlerts({ mmsi, limit: 1000 }),
                apiClient.getVesselTrack(mmsi, undefined, undefined, 1000),
                apiClient.getWatchlist().catch(() => [] as { mmsi: string }[]),
            ])
            setVessel(vesselData)
            setAlerts(alertsData)
            setTrack(trackData)
            setOnWatchlist(watchlistData.some((e) => e.mmsi === mmsi))
        } catch (error) {
            if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.error('Failed to load vessel data:', error)
            }
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return <div className="vessel-details-loading">Loading vessel details...</div>
    }

    if (!vessel) {
        return (
            <div className="vessel-details-error">
                <p>Vessel not found</p>
                <button onClick={onClose} className="btn-back">
                    Back
                </button>
            </div>
        )
    }

    // Prepare map data
    const trackPolyline: LatLngExpression[] = track
        .filter(p => p.lat && p.lon)
        .map(p => [p.lat, p.lon] as LatLngExpression)

    const alertPositions = alerts
        .filter(a => a.evidence?.p2_lat && a.evidence?.p2_lon)
        .map(a => ({
            alert: a,
            lat: a.evidence.p2_lat,
            lon: a.evidence.p2_lon,
        }))

    const bounds: LatLngExpression[] = trackPolyline.length > 0 
        ? trackPolyline 
        : vessel.lat && vessel.lon 
            ? [[vessel.lat, vessel.lon] as LatLngExpression]
            : []

    const center: LatLngExpression = vessel.lat && vessel.lon 
        ? [vessel.lat, vessel.lon] 
        : [40.7128, -74.0060]

    const alertStats = {
        total: alerts.length,
        high: alerts.filter(a => a.severity >= 70).length,
        medium: alerts.filter(a => a.severity >= 30 && a.severity < 70).length,
        low: alerts.filter(a => a.severity < 30).length,
        byType: alerts.reduce((acc, a) => {
            acc[a.type] = (acc[a.type] || 0) + 1
            return acc
        }, {} as Record<string, number>),
    }

    return (
        <div className="vessel-details">
            <div className="vessel-details-header">
                <button onClick={onClose} className="btn-back">
                    ← Back
                </button>
                <h2>Vessel Details: MMSI {vessel.mmsi}</h2>
            </div>

            <div className="vessel-watchlist-bar">
                {onWatchlist ? (
                    <span className="vessel-watchlist-badge">On watchlist</span>
                ) : (
                    <span className="vessel-watchlist-hint">Not on watchlist</span>
                )}
                <input
                    type="text"
                    placeholder="Label (optional)"
                    value={wlLabel}
                    onChange={(e) => setWlLabel(e.target.value)}
                    className="vessel-watchlist-input"
                />
                <select
                    value={wlPriority}
                    onChange={(e) => setWlPriority(e.target.value as 'low' | 'medium' | 'high')}
                    className="vessel-watchlist-select"
                >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                </select>
                <button
                    type="button"
                    className="btn-watchlist-add"
                    onClick={async () => {
                        try {
                            await apiClient.addWatchlistEntry({
                                mmsi: vessel.mmsi,
                                label: wlLabel.trim(),
                                priority: wlPriority,
                            })
                            setOnWatchlist(true)
                            setWlLabel('')
                        } catch (err) {
                            alert(err instanceof Error ? err.message : 'Could not update watchlist')
                        }
                    }}
                >
                    {onWatchlist ? 'Update watchlist' : 'Add to watchlist'}
                </button>
            </div>

            <div className="vessel-info-cards">
                <div className="info-card">
                    <div className="info-label">Current Position</div>
                    <div className="info-value">
                        {vessel.lat.toFixed(4)}, {vessel.lon.toFixed(4)}
                    </div>
                </div>
                {vessel.sog !== null && (
                    <div className="info-card">
                        <div className="info-label">Speed</div>
                        <div className="info-value">{vessel.sog.toFixed(1)} kn</div>
                    </div>
                )}
                {vessel.heading !== null && (
                    <div className="info-card">
                        <div className="info-label">Heading</div>
                        <div className="info-value">{vessel.heading.toFixed(1)}°</div>
                    </div>
                )}
                <div className="info-card">
                    <div className="info-label">Last Update</div>
                    <div className="info-value">
                        {new Date(vessel.timestamp).toLocaleString()}
                    </div>
                </div>
                <div className="info-card severity">
                    <div className="info-label">Alert Severity</div>
                    <div className={`info-value severity-${getSeverityLevel(vessel.last_alert_severity)}`}>
                        {vessel.last_alert_severity}
                    </div>
                </div>
            </div>

            <div className="vessel-tabs">
                <button
                    className={activeTab === 'overview' ? 'active' : ''}
                    onClick={() => setActiveTab('overview')}
                >
                    Overview
                </button>
                <button
                    className={activeTab === 'alerts' ? 'active' : ''}
                    onClick={() => setActiveTab('alerts')}
                >
                    Alerts ({alerts.length})
                </button>
                <button
                    className={activeTab === 'track' ? 'active' : ''}
                    onClick={() => setActiveTab('track')}
                >
                    Track ({track.length} points)
                </button>
            </div>

            <div className="vessel-tab-content">
                {activeTab === 'overview' && (
                    <div className="overview-content">
                        <div className="overview-section">
                            <h3>Alert Statistics</h3>
                            <div className="stats-grid">
                                <div className="stat-item">
                                    <div className="stat-value">{alertStats.total}</div>
                                    <div className="stat-label">Total Alerts</div>
                                </div>
                                <div className="stat-item">
                                    <div className="stat-value severity-high">{alertStats.high}</div>
                                    <div className="stat-label">High Severity</div>
                                </div>
                                <div className="stat-item">
                                    <div className="stat-value severity-medium">{alertStats.medium}</div>
                                    <div className="stat-label">Medium Severity</div>
                                </div>
                                <div className="stat-item">
                                    <div className="stat-value severity-low">{alertStats.low}</div>
                                    <div className="stat-label">Low Severity</div>
                                </div>
                            </div>
                        </div>

                        {Object.keys(alertStats.byType).length > 0 && (
                            <div className="overview-section">
                                <h3>Alerts by Type</h3>
                                <div className="type-list">
                                    {Object.entries(alertStats.byType).map(([type, count]) => (
                                        <div key={type} className="type-item">
                                            <span className="type-name">{type}</span>
                                            <span className="type-count">{typeof count === 'number' ? count : 0}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="overview-section">
                            <h3>Track Summary</h3>
                            <p>
                                {track.length} position points recorded
                                {track.length > 0 && (
                                    <>
                                        <br />
                                        First: {new Date(track[0].timestamp).toLocaleString()}
                                        <br />
                                        Last: {new Date(track[track.length - 1].timestamp).toLocaleString()}
                                    </>
                                )}
                            </p>
                        </div>
                    </div>
                )}

                {activeTab === 'alerts' && (
                    <div className="alerts-content">
                        {alerts.length === 0 ? (
                            <div className="empty-state">No alerts for this vessel</div>
                        ) : (
                            <div className="alerts-list">
                                {alerts.map((alert) => (
                                    <div key={alert.id} className={`alert-card severity-${getSeverityLevel(alert.severity)}`}>
                                        <div className="alert-header">
                                            <div className="alert-type">{alert.type}</div>
                                            <div className={`severity-badge severity-${getSeverityLevel(alert.severity)}`}>
                                                {alert.severity}
                                            </div>
                                        </div>
                                        <div className="alert-summary">{alert.summary}</div>
                                        <div className="alert-details">
                                            <div className="detail-item">
                                                <span className="label">Time:</span>
                                                <span>{new Date(alert.timestamp).toLocaleString()}</span>
                                            </div>
                                            <div className="detail-item">
                                                <span className="label">Status:</span>
                                                <span className={`status-badge status-${alert.status || 'new'}`}>
                                                    {alert.status || 'new'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'track' && (
                    <div className="track-content">
                        <div className="track-map">
                            <MapContainer
                                center={center}
                                zoom={trackPolyline.length > 0 ? 10 : 8}
                                style={{ height: '500px', width: '100%' }}
                            >
                                <TileLayer
                                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                />
                                {bounds.length > 0 && <MapBounds bounds={bounds} />}
                                
                                {/* Track polyline */}
                                {trackPolyline.length > 1 && (
                                    <Polyline
                                        positions={trackPolyline}
                                        color="#3b82f6"
                                        weight={3}
                                        opacity={0.7}
                                    />
                                )}

                                {/* Current position */}
                                {vessel.lat && vessel.lon && (
                                    <Marker
                                        position={[vessel.lat, vessel.lon]}
                                        icon={createVesselDivIcon(onWatchlist)}
                                    >
                                        <Popup>
                                            <div>
                                                <strong>Current Position</strong><br />
                                                MMSI: {vessel.mmsi}<br />
                                                {vessel.sog !== null && <>Speed: {vessel.sog.toFixed(1)} kn<br /></>}
                                            </div>
                                        </Popup>
                                    </Marker>
                                )}

                                {/* Alert positions */}
                                {alertPositions
                                    .filter(({ lat, lon }) => typeof lat === 'number' && typeof lon === 'number')
                                    .map(({ alert, lat, lon }) => (
                                    <Marker
                                        key={alert.id}
                                        position={[lat as number, lon as number]}
                                        icon={createAlertDivIcon(alert.severity)}
                                    >
                                        <Popup>
                                            <div>
                                                <strong>Alert:</strong> {alert.type}<br />
                                                <strong>Severity:</strong> {alert.severity}<br />
                                                <strong>Time:</strong> {new Date(alert.timestamp).toLocaleString()}
                                            </div>
                                        </Popup>
                                    </Marker>
                                ))}
                            </MapContainer>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
