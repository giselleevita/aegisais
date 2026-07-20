import { useCallback, useEffect, useRef, useState } from 'react'
import { GeoJSON, MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import type { LatLngExpression } from 'leaflet'
import type { GeoJsonObject } from 'geojson'
import 'leaflet/dist/leaflet.css'
import '@/shared/map/leafletSetup'
import MapBounds from '@/shared/map/MapBounds'
import { createAlertDivIcon, createSarDivIcon, createVesselDivIcon } from '@/shared/map/alertMarkers'
import { apiClient } from '@/core/api-client'
import { describeApiFailure } from '@/core/api-errors'
import type { Vessel, Alert, VesselPosition, CanonicalObservation, FusionEvent, IntegrationFeed } from '@/shared/types/common'
import './MapView.css'
import InfrastructureLayer from '@/features/itdae/components/InfrastructureLayer'
import EezLayer from '@/features/geodata/EezLayer'
import EnvironmentalOverlay from '@/features/geodata/EnvironmentalOverlay'

// Baltic Sea — sensible default for a maritime threat-detection tool
const BALTIC_CENTER: LatLngExpression = [57.0, 18.0]
const BALTIC_ZOOM = 5

function computeCentroid(points: [number, number][]): LatLngExpression {
    if (points.length === 0) return BALTIC_CENTER
    const [sumLat, sumLon] = points.reduce(
        ([la, lo], p) => {
            const [lat, lon] = p
            return [la + lat, lo + lon]
        },
        [0, 0]
    )
    return [sumLat / points.length, sumLon / points.length]
}

interface MapViewProps {
    selectedVessel?: string | null
    onVesselClick?: (mmsi: string) => void
    showInfrastructure?: boolean
}

export default function MapView({ selectedVessel, onVesselClick, showInfrastructure = false }: MapViewProps) {
    const offlineDemo = import.meta.env.VITE_OFFLINE_DEMO === 'true'
    const [vessels, setVessels] = useState<Vessel[]>([])
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [vesselTrack, setVesselTrack] = useState<VesselPosition[]>([])
    const [sarObservations, setSarObservations] = useState<CanonicalObservation[]>([])
    const [fusionEvents, setFusionEvents] = useState<FusionEvent[]>([])
    const [feeds, setFeeds] = useState<IntegrationFeed[]>([])
    const [loading, setLoading] = useState(true)
    const [showAlerts, setShowAlerts] = useState(true)
    const [showAis, setShowAis] = useState(true)
    const [showSar, setShowSar] = useState(true)
    const [showFusion, setShowFusion] = useState(true)
    const [showTracks, setShowTracks] = useState(false)
    const [infraVisible, setInfraVisible] = useState(showInfrastructure)
    const [eezVisible, setEezVisible] = useState(false)
    const [envOverlay, setEnvOverlay] = useState(true)
    const [watchMmsi, setWatchMmsi] = useState<Set<string>>(new Set())
    const [controlsOpen, setControlsOpen] = useState(true)
    const [loadError, setLoadError] = useState<string | null>(null)
    const [trackError, setTrackError] = useState<string | null>(null)
    const [offlineLand, setOfflineLand] = useState<GeoJsonObject | null>(null)
    const [offlineMapError, setOfflineMapError] = useState<string | null>(null)
    const pausedRef = useRef(false)

    useEffect(() => {
        if (!offlineDemo) return
        const controller = new AbortController()
        fetch('/maps/baltic-land.geojson', { signal: controller.signal })
            .then((response) => {
                if (!response.ok) throw new Error(`offline basemap returned ${response.status}`)
                return response.json() as Promise<GeoJsonObject>
            })
            .then((land) => {
                setOfflineLand(land)
                setOfflineMapError(null)
            })
            .catch((error: unknown) => {
                if (error instanceof DOMException && error.name === 'AbortError') return
                setOfflineMapError(error instanceof Error ? error.message : 'offline basemap unavailable')
            })
        return () => controller.abort()
    }, [offlineDemo])

    const loadData = useCallback(async () => {
        if (pausedRef.current) return
        try {
            setLoadError(null)
            const [vesselsData, alertsData, watchlistData, sarData, fusionData, feedData] = await Promise.all([
                apiClient.getVessels(0, 1000),
                apiClient.getAlerts({ limit: 500, status: 'new' }),
                apiClient.getWatchlist().catch(() => [] as { mmsi: string }[]),
                apiClient.getObservations('maritime.sar.gfw', 500).catch(() => [] as CanonicalObservation[]),
                apiClient.getFusionEvents(500).catch(() => [] as FusionEvent[]),
                apiClient.getIntegrationFeeds().catch(() => ({ timestamp: '', feeds: [] as IntegrationFeed[] })),
            ])
            setVessels(vesselsData)
            setAlerts(alertsData)
            setWatchMmsi(new Set(watchlistData.map((w) => w.mmsi)))
            setSarObservations(sarData)
            setFusionEvents(fusionData)
            setFeeds(feedData.feeds)
        } catch (error) {
            setVessels([])
            setAlerts([])
            setWatchMmsi(new Set())
            setSarObservations([])
            setFusionEvents([])
            setFeeds([])
            setLoadError(
                describeApiFailure(error, {
                    fallback: 'Unable to load map telemetry.',
                    unauthorized: 'Sign in to load the common operating picture.',
                    offline: 'Map telemetry degraded. Restore the API policy surface to repopulate vessels and alerts.',
                })
            )
            if (import.meta.env.DEV) console.error('Failed to load map data:', error)
        } finally {
            setLoading(false)
        }
    }, [])

    const loadVesselTrack = useCallback(async (mmsi: string) => {
        try {
            const track = await apiClient.getVesselTrack(mmsi, undefined, undefined, 1000)
            setVesselTrack(track)
            setTrackError(null)
        } catch (error) {
            setVesselTrack([])
            setTrackError(
                describeApiFailure(error, {
                    fallback: 'Unable to load vessel track.',
                    unauthorized: 'Sign in to inspect vessel track history.',
                    offline: 'Track history unavailable while the API policy surface is offline.',
                })
            )
            if (import.meta.env.DEV) console.error('Failed to load vessel track:', error)
        }
    }, [])

    // Pause polling when tab is hidden, resume when visible
    useEffect(() => {
        const handleVisibility = () => {
            pausedRef.current = document.hidden
            if (!document.hidden) void loadData()
        }
        document.addEventListener('visibilitychange', handleVisibility)
        return () => document.removeEventListener('visibilitychange', handleVisibility)
    }, [loadData])

    useEffect(() => {
        void loadData()
        const interval = setInterval(() => { void loadData() }, 10000)
        return () => clearInterval(interval)
    }, [loadData])

    useEffect(() => {
        if (selectedVessel) void loadVesselTrack(selectedVessel)
        else setVesselTrack([])
    }, [loadVesselTrack, selectedVessel])

    useEffect(() => {
        if (typeof window === 'undefined') return
        const compact = window.matchMedia('(max-width: 900px)')
        setControlsOpen(!compact.matches)
    }, [])

    if (loading) return <div className="map-loading">Loading map...</div>

    const bounds: [number, number][] = vessels
        .filter(v => v.lat && v.lon)
        .map(v => [v.lat, v.lon])

    // Use geographic centroid, not first vessel
    const mapCenter = computeCentroid(bounds)

    // Null-safe alert positions: guard against missing or malformed evidence
    const alertPositions = alerts.flatMap(a => {
        const lat = a.evidence?.p2_lat
        const lon = a.evidence?.p2_lon
        if (typeof lat !== 'number' || typeof lon !== 'number') return []
        return [{ alert: a, lat, lon }]
    })

    const trackPolyline: LatLngExpression[] = vesselTrack
        .filter(p => p.lat && p.lon)
        .map(p => [p.lat, p.lon] as LatLngExpression)

    const degradedFeeds = feeds.filter(feed => feed.status !== 'ready')
    const statusSummary = `${vessels.length} vessels, ${sarObservations.length} SAR detections, ${fusionEvents.length} fused events, ${alertPositions.length} alerts, ${selectedVessel ? 'selected vessel active' : 'no vessel selected'}`

    return (
        <div className="map-view">
            <p className="sr-only" role="status" aria-live="polite">{statusSummary}</p>
            {loadError && (
                <div className="map-banner map-banner--warning" role="status">
                    <strong>Map feed degraded.</strong>
                    <span>{loadError}</span>
                </div>
            )}
            {trackError && (
                <div className="map-banner" role="status">
                    <strong>Track history unavailable.</strong>
                    <span>{trackError}</span>
                </div>
            )}
            {degradedFeeds.length > 0 && (
                <div className="map-banner" role="status">
                    <strong>Sensor state</strong>
                    <span>{degradedFeeds.map(feed => `${feed.label}: ${feed.status}`).join(' · ')}</span>
                </div>
            )}
            {offlineDemo && (
                <div className="map-banner" role="status">
                    <strong>Offline basemap mode</strong>
                    <span>
                        {offlineMapError
                            ? `Local Baltic vector basemap degraded: ${offlineMapError}`
                            : offlineLand
                                ? 'Natural Earth Baltic vector basemap loaded locally; remote map tiles are disabled.'
                                : 'Loading the local Natural Earth Baltic vector basemap…'}
                    </span>
                </div>
            )}
            <details className="map-controls" open={controlsOpen} onToggle={(e) => setControlsOpen(e.currentTarget.open)}>
                <summary className="map-controls__summary">Map Layers</summary>
                <fieldset className="map-controls__fieldset" aria-label="Map display controls">
                    <legend className="sr-only">Map display controls</legend>
                    <label htmlFor="map-show-alerts">
                        <input id="map-show-alerts" type="checkbox" checked={showAlerts} onChange={(e) => setShowAlerts(e.target.checked)} />
                        Show Alerts
                    </label>
                    <label htmlFor="map-show-ais">
                        <input id="map-show-ais" type="checkbox" checked={showAis} onChange={(e) => setShowAis(e.target.checked)} />
                        AIS tracks
                    </label>
                    <label htmlFor="map-show-sar">
                        <input id="map-show-sar" type="checkbox" checked={showSar} onChange={(e) => setShowSar(e.target.checked)} />
                        SAR detections
                    </label>
                    <label htmlFor="map-show-fusion">
                        <input id="map-show-fusion" type="checkbox" checked={showFusion} onChange={(e) => setShowFusion(e.target.checked)} />
                        Fused cable risk
                    </label>
                    <label htmlFor="map-show-cables">
                        <input id="map-show-cables" type="checkbox" checked={infraVisible} onChange={(e) => setInfraVisible(e.target.checked)} />
                        Cable Zones
                    </label>
                    <label htmlFor="map-show-eez">
                        <input id="map-show-eez" type="checkbox" checked={eezVisible} onChange={(e) => setEezVisible(e.target.checked)} />
                        EEZ Boundaries
                    </label>
                    <label htmlFor="map-show-env">
                        <input id="map-show-env" type="checkbox" checked={envOverlay} onChange={(e) => setEnvOverlay(e.target.checked)} />
                        Env Context (right-click)
                    </label>
                    {/* Track toggle always visible so mobile users can access it */}
                    <label htmlFor="map-show-track" style={{ opacity: selectedVessel ? 1 : 0.4 }}>
                        <input
                            id="map-show-track"
                            type="checkbox"
                            checked={showTracks}
                            disabled={!selectedVessel}
                            onChange={(e) => setShowTracks(e.target.checked)}
                        />
                        Show Track {!selectedVessel && '(select a vessel)'}
                    </label>
                </fieldset>
            </details>
            <MapContainer
                center={mapCenter}
                zoom={bounds.length > 0 ? 8 : BALTIC_ZOOM}
                className={offlineDemo ? 'offline-basemap' : undefined}
                style={{ height: '100%', width: '100%' }}
            >
                {!offlineDemo && <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />}
                {offlineDemo && offlineLand && <GeoJSON
                    data={offlineLand}
                    attribution='Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com.'
                    style={{
                        color: '#486581',
                        weight: 1,
                        fillColor: '#15283b',
                        fillOpacity: 0.92,
                    }}
                />}
                {bounds.length > 0 && <MapBounds bounds={bounds} />}

                {showAis && vessels.map((vessel) => (
                    <Marker
                        key={vessel.mmsi}
                        position={[vessel.lat, vessel.lon]}
                        icon={createVesselDivIcon(watchMmsi.has(vessel.mmsi))}
                        eventHandlers={{ click: () => onVesselClick?.(vessel.mmsi) }}
                    >
                        <Popup>
                            <div>
                                <strong>MMSI:</strong> {vessel.mmsi}<br />
                                <strong>Position:</strong> {vessel.lat.toFixed(4)}, {vessel.lon.toFixed(4)}<br />
                                {vessel.sog !== null && <><strong>Speed:</strong> {vessel.sog.toFixed(1)} kn<br /></>}
                                <strong>Alert Severity:</strong> {vessel.last_alert_severity}
                            </div>
                        </Popup>
                    </Marker>
                ))}

                {showSar && sarObservations.map((observation) => {
                    const [lon, lat] = observation.geometry.coordinates
                    const unmatched = observation.properties?.matched !== true
                    return (
                        <Marker key={observation.id} position={[lat, lon]} icon={createSarDivIcon(unmatched)}>
                            <Popup>
                                <div>
                                    <strong>SAR detection</strong><br />
                                    <strong>AIS match:</strong> {unmatched ? 'None' : 'Matched'}<br />
                                    <strong>Confidence:</strong> {Math.round(observation.confidence.score * 100)}%<br />
                                    <strong>Source:</strong> {observation.provenance.source}<br />
                                    <strong>Observed:</strong> {new Date(observation.observedAt).toLocaleString()}
                                </div>
                            </Popup>
                        </Marker>
                    )
                })}

                {showFusion && fusionEvents.map((event) => {
                    const [lon, lat] = event.geometry.coordinates
                    const severity = event.severity === 'critical' ? 95 : event.severity === 'high' ? 80 : event.severity === 'medium' ? 55 : 25
                    return (
                        <Marker key={event.id} position={[lat, lon]} icon={createAlertDivIcon(severity)}>
                            <Popup>
                                <div>
                                    <strong>{event.eventType}</strong><br />
                                    <strong>Confidence:</strong> {Math.round(event.confidence.score * 100)}%<br />
                                    <strong>Why:</strong> {String(event.attributes.reason || 'Fused sensor event')}<br />
                                    <strong>Sensors:</strong> {Array.isArray(event.attributes.sensorSupport) ? event.attributes.sensorSupport.join(' + ') : 'See evidence'}
                                </div>
                            </Popup>
                        </Marker>
                    )
                })}

                {showAlerts && alertPositions.map(({ alert, lat, lon }) => (
                    <Marker
                        key={alert.id}
                        position={[lat, lon]}
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

                {showTracks && selectedVessel && trackPolyline.length > 1 && (
                    <Polyline positions={trackPolyline} color="#3b82f6" weight={3} opacity={0.7} />
                )}

                <InfrastructureLayer visible={infraVisible} />
                <EezLayer visible={eezVisible} />
                <EnvironmentalOverlay visible={envOverlay} />
            </MapContainer>
        </div>
    )
}
