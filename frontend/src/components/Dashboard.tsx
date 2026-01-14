import { useEffect, useState } from 'react'
import { apiClient } from '../api/client'
import type { AlertStats, WebSocketMessage } from '../types'
import './Dashboard.css'

interface DashboardProps {
    lastMessage: WebSocketMessage | null
}

export default function Dashboard({ lastMessage }: DashboardProps) {
    const [stats, setStats] = useState<AlertStats | null>(null)
    const [vesselCount, setVesselCount] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        loadStats()
        loadVesselCount()
        const interval = setInterval(() => {
            loadStats()
            loadVesselCount()
        }, 5000) // Refresh every 5 seconds

        return () => clearInterval(interval)
    }, [])

    useEffect(() => {
        if (lastMessage?.kind === 'alert' || lastMessage?.kind === 'tick') {
            loadStats()
            loadVesselCount()
        }
    }, [lastMessage])

    const loadStats = async () => {
        try {
            const data = await apiClient.getAlertStats()
            setStats(data)
            setError(null)
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to load stats'
            setError(errorMessage)
            if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.error('Failed to load stats:', err)
            }
        } finally {
            setLoading(false)
        }
    }

    const loadVesselCount = async () => {
        try {
            // Get total count by fetching with a high limit
            const allVessels = await apiClient.getVessels(0, 5000)
            setVesselCount(allVessels.length)
        } catch (err) {
            if (import.meta.env.DEV) {
                // eslint-disable-next-line no-console
                console.error('Failed to load vessel count:', err)
            }
        }
    }

    if (loading) {
        return <div className="dashboard-loading">Loading dashboard...</div>
    }

    return (
        <div className="dashboard">
            <h2>Dashboard</h2>

            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-label">Total Vessels</div>
                    <div className="stat-value">{vesselCount}</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Total Alerts</div>
                    <div className="stat-value">{stats?.total || 0}</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">High Severity</div>
                    <div className="stat-value severity-high">{stats?.by_severity_range?.high || 0}</div>
                </div>

                <div className="stat-card">
                    <div className="stat-label">Average Severity</div>
                    <div className="stat-value">{stats?.average_severity?.toFixed(1) || '0.0'}</div>
                </div>
            </div>

            {error && (
                <div className="dashboard-error" role="alert">
                    Error: {error}
                </div>
            )}

            {stats?.by_type && Object.keys(stats.by_type).length > 0 && (
                <div className="alert-types">
                    <h3>Alerts by Type</h3>
                    <div className="type-list">
                        {Object.entries(stats.by_type).map(([type, count]) => (
                            <div key={type} className="type-item">
                                <span className="type-name">{type}</span>
                                <span className="type-count">{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {lastMessage && (
                <div className="recent-activity">
                    <h3>Recent Activity</h3>
                    <div className="activity-item">
                        {lastMessage.kind === 'alert' && (
                            <div>
                                <strong>Alert:</strong> {lastMessage.data?.type} - {lastMessage.data?.summary}
                                <br />
                                <small>MMSI: {lastMessage.data?.mmsi} | Severity: {lastMessage.data?.severity}</small>
                            </div>
                        )}
                        {lastMessage.kind === 'tick' && (
                            <div>
                                <strong>Replay Progress:</strong> {lastMessage.processed} points processed
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

