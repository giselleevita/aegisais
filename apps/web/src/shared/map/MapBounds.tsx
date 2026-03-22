import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import type { LatLngExpression, LatLngBoundsExpression } from 'leaflet'

interface MapBoundsProps {
    bounds: LatLngExpression[]
}

/**
 * Fits the map to the given bounds when they change (vessel positions, tracks, etc.).
 */
export default function MapBounds({ bounds }: MapBoundsProps) {
    const map = useMap()
    useEffect(() => {
        if (bounds.length > 0) {
            const lats = bounds.map((b) => (Array.isArray(b) ? b[0] : b.lat))
            const lons = bounds.map((b) => (Array.isArray(b) ? b[1] : b.lng))
            const minLat = Math.min(...lats)
            const maxLat = Math.max(...lats)
            const minLon = Math.min(...lons)
            const maxLon = Math.max(...lons)
            map.fitBounds([[minLat, minLon], [maxLat, maxLon]] as LatLngBoundsExpression)
        }
    }, [bounds, map])
    return null
}
