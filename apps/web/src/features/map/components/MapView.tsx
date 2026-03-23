import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import type { LatLngExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import '@/shared/map/leafletSetup'
import MapBounds from '@/shared/map/MapBounds'
import { createAlertDivIcon, createVesselDivIcon } from '@/shared/map/alertMarkers'
import { apiClient } from '@/core/api-client'
import type { Vessel, Alert, VesselPosition } from '@/shared/types/common'
import './MapView.css'
import InfrastructureLayer from '@/features/itdae/components/InfrastructureLayer'

interface MapViewProps {
    selectedVessel?: string | null
    onVesselClick?: (mmsi: string) => void
    showInfrastructure?: boolean
}

export default function MapView({ selectedVessel, onVesselClick, showInfrastructure = false }: MapViewProps) {
    const [vessels, setVessels] = useState<Vessel[]>([])
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [vesselTrack, setVesselTrack] = useState<VesselPosition[]>([])
    const [loading, setLoading] = useState(true)
    const [showAlerts, setShowAlerts] = useState(true)
    const [showTracks, setShowTracks] = useState(false)
    const [infraVisible, setInfraVisible] = useState(showInfrastructure)
    const [watchMmsi, setWatchMmsi] = useState<Set<string>>(new Set())
    const [controlsOpen, setControlsOpen] = useState(true)

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

    useEffect(() => {
        if (typeof window === 'undefined') return
        const compact = window.matchMedia('(max-width: 900px)')
        setControlsOpen(!compact.matches)
    }, [])

    const loadData = async () => {
        try {
            const [vesselsData, alertsData, watchlistData] = await Promise.all([
                apiClient.getVessels(0, 1000),
                apiClient.getAlerts({ limit: 500, status: 'new' }),
                apiClient.getWatchlist().catch(() => [] as { mmsi: string }[]),
            ])
            setVessels(vesselsData)
            setAlerts(alertsData)
            setWatchMmsi(new Set(watchlistData.map((w) => w.mmsi)))
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

    const statusSummary = `${vessels.length} vessels, ${alertPositions.length} alerts, ${selectedVessel ? 'selected vessel active' : 'no vessel selected'}`

    return (
        <div className="map-view">
            <p className="sr-only" role="status" aria-live="polite">
                {statusSummary}
            </p>
            <details className="map-controls" open={controlsOpen} onToggle={(e) => setControlsOpen(e.currentTarget.open)}>
                <summary className="map-controls__summary">Map Layers</summary>
                <fieldset className="map-controls__fieldset" aria-label="Map display controls">
                    <legend className="sr-only">Map display controls</legend>
                    <label htmlFor="map-show-alerts">
                        <input
                            id="map-show-alerts"
                            type="checkbox"
                            checked={showAlerts}
                            onChange={(e) => setShowAlerts(e.target.checked)}
                        />
                        Show Alerts
                    </label>
                    <label htmlFor="map-show-cables">
                        <input
                            id="map-show-cables"
                            type="checkbox"
                            checked={infraVisible}
                            onChange={(e) => setInfraVisible(e.target.checked)}
                        />
                        Cable Zones
                    </label>
                    {selectedVessel && (
                        <label htmlFor="map-show-track">
                            <input
                                id="map-show-track"
                                type="checkbox"
                                checked={showTracks}
                                onChange={(e) => setShowTracks(e.target.checked)}
                            />
                            Show Track
                        </label>
                    )}
                </fieldset>
            </details>
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
                        icon={createVesselDivIcon(watchMmsi.has(vessel.mmsi))}
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
                            icon={createAlertDivIcon(alert.severity)}
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

                {/* ITDAE cable corridor geofence zones */}
                <InfrastructureLayer visible={infraVisible} />
            </MapContainer>
        </div>
    )
}
