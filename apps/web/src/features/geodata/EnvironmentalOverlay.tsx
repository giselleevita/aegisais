import { useState } from 'react'
import { useMapEvents, Popup } from 'react-leaflet'
import { apiClient } from '@/core/api-client'

interface EnvironmentalContextData {
    eez: { name: string; sovereign: string; iso3: string } | null
    international_waters: boolean
    weather: {
        wave_height_m?: number
        wind_speed_kmh?: number
        sea_state?: string
        sea_state_description?: string
    } | null
    depth: {
        depth_m?: number
        depth_category?: string
        is_land?: boolean
    } | null
}

interface EnvironmentalOverlayProps {
    visible?: boolean
}

export default function EnvironmentalOverlay({ visible = true }: EnvironmentalOverlayProps) {
    const [data, setData] = useState<EnvironmentalContextData | null>(null)
    const [position, setPosition] = useState<{ lat: number; lon: number } | null>(null)
    const [loading, setLoading] = useState(false)

    useMapEvents({
        contextmenu: async (e) => {
            if (!visible) return
            const { lat, lng: lon } = e.latlng
            setPosition({ lat, lon })
            setLoading(true)
            try {
                const ctx = await apiClient.getEnvironmentalContext(lat, lon)
                setData(ctx)
            } catch {
                setData(null)
            } finally {
                setLoading(false)
            }
        },
    })

    if (!visible || !position) return null

    return (
        <Popup
            position={[position.lat, position.lon]}
            eventHandlers={{ remove: () => setPosition(null) }}
        >
            <div style={{ fontSize: 12, minWidth: 200, maxWidth: 280 }}>
                <strong style={{ fontSize: 13 }}>Environmental Context</strong>
                <hr style={{ margin: '4px 0', border: 'none', borderTop: '1px solid #ddd' }} />

                {loading ? (
                    <div style={{ padding: '8px 0', color: '#888' }}>Loading...</div>
                ) : !data ? (
                    <div style={{ padding: '8px 0', color: '#c00' }}>Unavailable</div>
                ) : (
                    <>
                        {/* EEZ */}
                        <div style={{ marginBottom: 6 }}>
                            <strong>Jurisdiction:</strong>{' '}
                            {data.international_waters
                                ? 'International Waters'
                                : data.eez
                                  ? `${data.eez.name} (${data.eez.iso3})`
                                  : 'Unknown'}
                        </div>

                        {/* Weather */}
                        {data.weather ? (
                            <div style={{ marginBottom: 6 }}>
                                <strong>Weather:</strong>
                                <br />
                                {data.weather.sea_state && (
                                    <span>Sea state: {data.weather.sea_state} ({data.weather.sea_state_description})<br /></span>
                                )}
                                {data.weather.wave_height_m != null && (
                                    <span>Waves: {data.weather.wave_height_m.toFixed(1)}m<br /></span>
                                )}
                                {data.weather.wind_speed_kmh != null && (
                                    <span>Wind: {data.weather.wind_speed_kmh.toFixed(0)} km/h</span>
                                )}
                            </div>
                        ) : (
                            <div style={{ marginBottom: 6, color: '#888' }}>Weather: N/A</div>
                        )}

                        {/* Bathymetry */}
                        {data.depth ? (
                            <div>
                                <strong>Depth:</strong>{' '}
                                {data.depth.is_land
                                    ? '⚠ Land'
                                    : data.depth.depth_m != null
                                      ? `${Math.abs(data.depth.depth_m).toFixed(0)}m (${data.depth.depth_category ?? 'unknown'})`
                                      : 'N/A'}
                            </div>
                        ) : (
                            <div style={{ color: '#888' }}>Depth: N/A</div>
                        )}
                    </>
                )}

                <div style={{ marginTop: 6, fontSize: 10, color: '#aaa' }}>
                    {position.lat.toFixed(4)}, {position.lon.toFixed(4)}
                </div>
            </div>
        </Popup>
    )
}
