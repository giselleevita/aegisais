import { useState, useEffect } from 'react'
import { Rectangle, Tooltip } from 'react-leaflet'
import type { LatLngBoundsExpression } from 'leaflet'
import { apiClient } from '@/core/api-client'

const SOVEREIGN_COLOURS: Record<string, string> = {
    GBR: '#1e3a5f',
    NOR: '#ba0c2f',
    DNK: '#c60c30',
    DEU: '#000000',
    SWE: '#006aa7',
    FIN: '#003580',
    EST: '#0072ce',
    LVA: '#9e3039',
    LTU: '#006a44',
    POL: '#dc143c',
    NLD: '#ff6600',
    FRA: '#002395',
    ESP: '#aa151b',
    ITA: '#008c45',
    GRC: '#0d5eaf',
    TUR: '#e30a17',
    USA: '#3c3b6e',
    CAN: '#ff0000',
    RUS: '#0039a6',
}

function getColour(iso3: string): string {
    return SOVEREIGN_COLOURS[iso3] ?? '#888888'
}

interface EezZone {
    name: string
    sovereign: string
    iso3: string
    mrgid?: number
    bbox?: [number, number, number, number]
}

interface EezLayerProps {
    visible?: boolean
}

export default function EezLayer({ visible = true }: EezLayerProps) {
    const [zones, setZones] = useState<EezZone[]>([])

    useEffect(() => {
        if (!visible) return
        apiClient
            .getEezZones()
            .then((data) => setZones(data.zones ?? []))
            .catch(() => {
                if (import.meta.env.DEV) {
                    console.warn('EezLayer: EEZ zones unavailable')
                }
            })
    }, [visible])

    if (!visible || zones.length === 0) return null

    return (
        <>
            {zones
                .filter((z) => z.bbox)
                .map((zone) => {
                    const [minLon, minLat, maxLon, maxLat] = zone.bbox!
                    const bounds: LatLngBoundsExpression = [
                        [minLat, minLon],
                        [maxLat, maxLon],
                    ]
                    const colour = getColour(zone.iso3)

                    return (
                        <Rectangle
                            key={zone.mrgid ?? zone.iso3}
                            bounds={bounds}
                            pathOptions={{
                                color: colour,
                                fillColor: colour,
                                fillOpacity: 0.06,
                                weight: 1.5,
                                dashArray: '8 4',
                            }}
                        >
                            <Tooltip sticky>
                                <div style={{ fontSize: 12, minWidth: 140 }}>
                                    <strong>{zone.name}</strong>
                                    <br />
                                    <span style={{ color: '#666' }}>
                                        {zone.sovereign} ({zone.iso3})
                                    </span>
                                </div>
                            </Tooltip>
                        </Rectangle>
                    )
                })}
        </>
    )
}
