import { useEffect, useState } from 'react'
import { apiClient } from '../api/client'
import type { Vessel, Alert, VesselPosition } from '../api/client'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import type { LatLngExpression, LatLngBoundsExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import './VesselDetails.css'

// Fix for default marker icons
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

function MapBounds({ bounds }: { bounds: LatLngExpression[] }) {
    const map = useMap()
    useEffect(() => {
        if (bounds.length > 0) {
            // Convert to proper bounds format: [[minLat, minLon], [maxLat, maxLon]]
            const lats = bounds.map(b => Array.isArray(b) ? b[0] : b.lat)
            const lons = bounds.map(b => Array.isArray(b) ? b[1] : b.lng)
            const minLat = Math.min(...lats)
            const maxLat = Math.max(...lats)
            const minLon = Math.min(...lons)
            const maxLon = Math.max(...lons)
            map.fitBounds([[minLat, minLon], [maxLat, maxLon]] as LatLngBoundsExpression)
        }
    }, [bounds, map])
    return null
}

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
            const [vesselData, alertsData, trackData] = await Promise.all([
                apiClient.getVessel(mmsi),
                apiClient.getAlerts({ mmsi, limit: 1000 }),
                apiClient.getVesselTrack(mmsi, undefined, undefined, 1000)
            ])
            setVessel(vesselData)
            setAlerts(alertsData)
            setTrack(trackData)
        } catch (error) {
            console.error('Failed to load vessel data:', error)
        } finally {
            setLoading(false)
        }
    }

    const getSeverityLevel = (severity: number): string => {
        if (severity >= 70) return 'high'
        if (severity >= 30) return 'medium'
        return 'low'
    }

    const getAlertIcon = (severity: number) => {
        const color = severity >= 70 ? '#dc2626' : severity >= 30 ? '#f59e0b' : '#10b981'
        return L.divIcon({
            className: 'alert-marker',
            html: `<div style="background-color: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
            iconSize: [12, 12],
        })
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
                                            <span className="type-count">{count}</span>
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
                                    <Marker position={[vessel.lat, vessel.lon]}>
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
                                {alertPositions.map(({ alert, lat, lon }) => (
                                    <Marker
                                        key={alert.id}
                                        position={[lat, lon]}
                                        icon={getAlertIcon(alert.severity)}
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
