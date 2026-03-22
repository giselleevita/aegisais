import L from 'leaflet'

/** Severity colour for map markers (matches AlertsPanel tier thresholds: 30 / 70). */
export function getSeverityColorHex(severity: number): string {
    if (severity >= 70) return '#dc2626'
    if (severity >= 30) return '#f59e0b'
    return '#10b981'
}

export function createAlertDivIcon(severity: number): L.DivIcon {
    const color = getSeverityColorHex(severity)
    return L.divIcon({
        className: 'alert-marker',
        html: `<div style="background-color: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
        iconSize: [12, 12],
    })
}

/** Vessel position marker: purple when MMSI is on the analyst watchlist, blue otherwise. */
export function createVesselDivIcon(isWatchlisted: boolean): L.DivIcon {
    const color = isWatchlisted ? '#a855f7' : '#2563eb'
    return L.divIcon({
        className: 'vessel-marker',
        html: `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.35);"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
    })
}
