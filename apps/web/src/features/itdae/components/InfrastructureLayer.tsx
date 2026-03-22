import { useState, useEffect } from 'react'
import { Polygon, Tooltip } from 'react-leaflet'
import type { LatLngExpression } from 'leaflet'
import type { ItdaeGeofenceZone } from '@/features/itdae/types'
import { apiClient } from '@/core/api-client'

const RISK_COLOURS = {
    critical: { fill: '#ff4d4d', stroke: '#cc0000' },
    high: { fill: '#ff8c42', stroke: '#cc5500' },
    medium: { fill: '#f0c040', stroke: '#cc9900' },
} as const

/**
 * InfrastructureLayer
 *
 * Renders Baltic Sea cable corridor geofence polygons on top of a
 * react-leaflet MapContainer. Fetches zone definitions from the ITDAE API.
 *
 * Usage — place inside a <MapContainer>:
 *   <InfrastructureLayer visible={showInfrastructure} />
 */
interface InfrastructureLayerProps {
    visible?: boolean
}

export default function InfrastructureLayer({ visible = true }: InfrastructureLayerProps) {
    const [zones, setZones] = useState<ItdaeGeofenceZone[]>([])

    useEffect(() => {
        if (!visible) return
        apiClient
            .getItdaeBalticGeofences()
            .then((data) => setZones(data.zones ?? []))
            .catch(() => {
                if (import.meta.env.DEV) {
                    console.warn('InfrastructureLayer: ITDAE geofences unavailable, using empty zones')
                }
            })
    }, [visible])

    if (!visible) return null

    return (
        <>
            {zones.map((zone) => {
                const colours = RISK_COLOURS[zone.risk_level] ?? RISK_COLOURS.medium

                // react-leaflet Polygon expects [lat, lon]; our data is [lon, lat]
                const positions: LatLngExpression[] = zone.polygon.map(
                    ([lon, lat]) => [lat, lon] as LatLngExpression,
                )

                return (
                    <Polygon
                        key={zone.id}
                        positions={positions}
                        pathOptions={{
                            color: colours.stroke,
                            fillColor: colours.fill,
                            fillOpacity: 0.15,
                            weight: 2,
                            dashArray: zone.risk_level === 'critical' ? undefined : '6 4',
                        }}
                    >
                        <Tooltip sticky>
                            <div style={{ fontSize: 12, minWidth: 160 }}>
                                <strong>{zone.name}</strong>
                                <br />
                                <span style={{ color: colours.stroke, textTransform: 'capitalize' }}>
                                    ⚠ {zone.risk_level} risk
                                </span>
                                <br />
                                <span style={{ color: '#666' }}>{zone.description}</span>
                            </div>
                        </Tooltip>
                    </Polygon>
                )
            })}
        </>
    )
}
