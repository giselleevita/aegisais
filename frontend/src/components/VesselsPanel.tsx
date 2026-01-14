import { useEffect, useState } from 'react'
import { apiClient } from '../api/client'
import type { Vessel } from '../api/client'
import './VesselsPanel.css'

interface VesselsPanelProps {
    onVesselClick?: (mmsi: string) => void
}

export default function VesselsPanel({ onVesselClick }: VesselsPanelProps) {
    const [vessels, setVessels] = useState<Vessel[]>([])
    const [loading, setLoading] = useState(true)
    const [minSeverity, setMinSeverity] = useState(0)
    const [searchMmsi, setSearchMmsi] = useState('')

    useEffect(() => {
        loadVessels()
        const interval = setInterval(loadVessels, 5000)
        return () => clearInterval(interval)
    }, [minSeverity])

    const loadVessels = async () => {
        try {
            setLoading(true)
            const data = await apiClient.getVessels(minSeverity, 500)
            setVessels(data)
        } catch (error) {
            console.error('Failed to load vessels:', error)
        } finally {
            setLoading(false)
        }
    }

    const filteredVessels = vessels.filter(v =>
        !searchMmsi || v.mmsi.includes(searchMmsi)
    )

    return (
        <div className="vessels-panel">
            <div className="panel-header">
                <h2>Vessels</h2>
                <div className="panel-controls">
                    <input
                        type="text"
                        placeholder="Search MMSI..."
                        value={searchMmsi}
                        onChange={(e) => setSearchMmsi(e.target.value)}
                        className="search-input"
                    />
                    <select
                        value={minSeverity}
                        onChange={(e) => setMinSeverity(Number(e.target.value))}
                        className="severity-filter"
                    >
                        <option value={0}>All Vessels</option>
                        <option value={30}>Low Severity (30+)</option>
                        <option value={50}>Medium Severity (50+)</option>
                        <option value={70}>High Severity (70+)</option>
                    </select>
                </div>
            </div>

            {loading ? (
                <div className="loading">Loading vessels...</div>
            ) : (
                <div className="vessels-list">
                    {filteredVessels.length === 0 ? (
                        <div className="empty-state">No vessels found</div>
                    ) : (
                        filteredVessels.map((vessel) => (
                            <div 
                                key={vessel.mmsi} 
                                className="vessel-card"
                                onClick={() => onVesselClick?.(vessel.mmsi)}
                                style={{ cursor: onVesselClick ? 'pointer' : 'default' }}
                            >
                                <div className="vessel-header">
                                    <span className="vessel-mmsi">MMSI: {vessel.mmsi}</span>
                                    <span className={`severity-badge severity-${getSeverityLevel(vessel.last_alert_severity)}`}>
                                        {vessel.last_alert_severity}
                                    </span>
                                </div>
                                <div className="vessel-details">
                                    <div className="detail-item">
                                        <span className="label">Position:</span>
                                        <span>{vessel.lat.toFixed(4)}, {vessel.lon.toFixed(4)}</span>
                                    </div>
                                    {vessel.sog !== null && (
                                        <div className="detail-item">
                                            <span className="label">Speed:</span>
                                            <span>{vessel.sog.toFixed(1)} kn</span>
                                        </div>
                                    )}
                                    {vessel.heading !== null && (
                                        <div className="detail-item">
                                            <span className="label">Heading:</span>
                                            <span>{vessel.heading.toFixed(1)}°</span>
                                        </div>
                                    )}
                                    <div className="detail-item">
                                        <span className="label">Last Update:</span>
                                        <span>{new Date(vessel.timestamp).toLocaleString()}</span>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}

function getSeverityLevel(severity: number): string {
    if (severity >= 70) return 'high'
    if (severity >= 30) return 'medium'
    return 'low'
}

