import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import type { LatLngExpression, LatLngBoundsExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { apiClient } from '../api/client'
import type { Vessel, Alert, VesselPosition } from '../types'
import './MapView.css'
import L from 'leaflet'

// Fix for default marker icons in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

interface MapViewProps {
    selectedVessel?: string | null
    onVesselClick?: (mmsi: string) => void
}

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

export default function MapView({ selectedVessel, onVesselClick }: MapViewProps) {
    const [vessels, setVessels] = useState<Vessel[]>([])
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [vesselTrack, setVesselTrack] = useState<VesselPosition[]>([])
    const [loading, setLoading] = useState(true)
    const [showAlerts, setShowAlerts] = useState(true)
    const [showTracks, setShowTracks] = useState(false)

    useEffect(() => {
        loadData()
        const interval = setInterval(loadData, 10000) // Refresh every 10 seconds
        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        if (selectedVessel) {
            loadVesselTrack(selectedVessel)
        } else {
            setVesselTrack([])
        }
    }, [selectedVessel])

    const loadData = async () => {
        try {
            const [vesselsData, alertsData] = await Promise.all([
                apiClient.getVessels(0, 1000),
                apiClient.getAlerts({ limit: 500, status: 'new' })
            ])
            setVessels(vesselsData)
            setAlerts(alertsData)
        } catch (error) {
            if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.error('Failed to load map data:', error)
            }
        } finally {
            setLoading(false)
        }
    }

    const loadVesselTrack = async (mmsi: string) => {
        try {
            const track = await apiClient.getVesselTrack(mmsi, undefined, undefined, 1000)
            setVesselTrack(track)
        } catch (error) {
            if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.error('Failed to load vessel track:', error)
            }
        }
    }

    const getSeverityColor = (severity: number): string => {
        if (severity >= 70) return '#dc2626' // red
        if (severity >= 30) return '#f59e0b' // amber
        return '#10b981' // green
    }

    const getAlertIcon = (severity: number) => {
        return L.divIcon({
            className: 'alert-marker',
            html: `<div style="background-color: ${getSeverityColor(severity)}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
            iconSize: [12, 12],
        })
    }

    if (loading) {
        return <div className="map-loading">Loading map...</div>
    }

    // Calculate bounds from vessels
    const bounds: LatLngExpression[] = vessels
        .filter(v => v.lat && v.lon)
        .map(v => [v.lat, v.lon] as LatLngExpression)

    // Get alert positions from evidence
    const alertPositions = alerts
        .filter(a => a.evidence?.p2_lat && a.evidence?.p2_lon)
        .map(a => ({
            alert: a,
            lat: a.evidence.p2_lat,
            lon: a.evidence.p2_lon,
        }))

    // Get track polyline for selected vessel
    const trackPolyline: LatLngExpression[] = vesselTrack
        .filter(p => p.lat && p.lon)
        .map(p => [p.lat, p.lon] as LatLngExpression)

    const defaultCenter: LatLngExpression = bounds.length > 0 
        ? bounds[0] 
        : [40.7128, -74.0060] // Default to NYC

    return (
        <div className="map-view">
            <div className="map-controls">
                <label>
                    <input
                        type="checkbox"
                        checked={showAlerts}
                        onChange={(e) => setShowAlerts(e.target.checked)}
                    />
                    Show Alerts
                </label>
                {selectedVessel && (
                    <label>
                        <input
                            type="checkbox"
                            checked={showTracks}
                            onChange={(e) => setShowTracks(e.target.checked)}
                        />
                        Show Track
                    </label>
                )}
            </div>
            <MapContainer
                center={defaultCenter}
                zoom={bounds.length > 0 ? 8 : 2}
                style={{ height: '100%', width: '100%' }}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {bounds.length > 0 && <MapBounds bounds={bounds} />}
                
                {/* Vessel markers */}
                {vessels.map((vessel) => (
                    <Marker
                        key={vessel.mmsi}
                        position={[vessel.lat, vessel.lon]}
                        eventHandlers={{
                            click: () => onVesselClick?.(vessel.mmsi),
                        }}
                    >
                        <Popup>
                            <div>
                                <strong>MMSI:</strong> {vessel.mmsi}<br />
                                <strong>Position:</strong> {vessel.lat.toFixed(4)}, {vessel.lon.toFixed(4)}<br />
                                {vessel.sog !== null && (
                                    <>
                                        <strong>Speed:</strong> {vessel.sog.toFixed(1)} kn<br />
                                    </>
                                )}
                                <strong>Alert Severity:</strong> {vessel.last_alert_severity}
                            </div>
                        </Popup>
                    </Marker>
                ))}

                {/* Alert markers */}
                {showAlerts && alertPositions
                    .filter(({ lat, lon }) => typeof lat === 'number' && typeof lon === 'number')
                    .map(({ alert, lat, lon }) => (
                    <Marker
                        key={alert.id}
                        position={[lat as number, lon as number]}
                        icon={getAlertIcon(alert.severity)}
                    >
                        <Popup>
                            <div>
                                <strong>Alert:</strong> {alert.type}<br />
                                <strong>Severity:</strong> {alert.severity}<br />
                                <strong>MMSI:</strong> {alert.mmsi}<br />
                                <strong>Summary:</strong> {alert.summary}
                            </div>
                        </Popup>
                    </Marker>
                ))}

                {/* Vessel track polyline */}
                {showTracks && selectedVessel && trackPolyline.length > 1 && (
                    <Polyline
                        positions={trackPolyline}
                        color="#3b82f6"
                        weight={3}
                        opacity={0.7}
                    />
                )}
            </MapContainer>
        </div>
    )
}
