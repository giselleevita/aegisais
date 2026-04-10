import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '@/core/api-client'
import { describeApiFailure } from '@/core/api-errors'
import type { Alert, AlertFilters, WebSocketMessage } from '@/shared/types/common'
import {
    formatAlertType,
    getAlertClassification,
    getSeverityLevel,
    renderEvidence,
} from '@/features/alerts/lib/alertEvidence'
import './AlertsPanel.css'

type AlertsPanelProps = {
    /** Merge alert status changes broadcast from the API after PATCH /alerts/{id}/status */
    streamMessage?: WebSocketMessage | null
    /** When set (AML console), links each row to a full investigation route. */
    linkToAlert?: (alertId: number) => string
    /** When set, links to map context for the vessel MMSI (e.g. `/map?mmsi=`). */
    linkToMapForMmsi?: (mmsi: string) => string
    /** Apply quick triage filter presets from parent workflows. */
    quickPreset?: 'critical-new' | 'high-open' | 'last-hour' | 'clear' | null
}

export default function AlertsPanel({
    streamMessage = null,
    linkToAlert,
    linkToMapForMmsi,
    quickPreset = null,
}: AlertsPanelProps) {
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [loading, setLoading] = useState(true)
    const [filterType, setFilterType] = useState<string>('')
    const [filterStatus, setFilterStatus] = useState<string>('')
    const [minSeverity, setMinSeverity] = useState(0)
    const [startTime, setStartTime] = useState<string>('')
    const [endTime, setEndTime] = useState<string>('')
    const [editingAlert, setEditingAlert] = useState<number | null>(null)
    const [alertNotes, setAlertNotes] = useState<string>('')
    const [activeAlertIdx, setActiveAlertIdx] = useState(0)
    const [loadError, setLoadError] = useState<string | null>(null)

    const isEditableTarget = (target: EventTarget | null): boolean => {
        if (!(target instanceof HTMLElement)) return false
        const tag = target.tagName.toLowerCase()
        return target.isContentEditable || tag === 'input' || tag === 'textarea' || tag === 'select'
    }

    const loadAlerts = useCallback(async () => {
        try {
            setLoading(true)
            setLoadError(null)
            const params: AlertFilters = { limit: 100 }
            if (filterType) params.alert_type = filterType
            if (filterStatus) params.status = filterStatus
            if (minSeverity > 0) params.min_severity = minSeverity
            if (startTime) params.start_time = new Date(startTime).toISOString()
            if (endTime) params.end_time = new Date(endTime).toISOString()
            const data = await apiClient.getAlerts(params)
            setAlerts(data)
        } catch (err) {
            setAlerts([])
            setLoadError(
                describeApiFailure(err, {
                    fallback: 'Unable to load alerts.',
                    unauthorized: 'Sign in to load the alert queue.',
                    offline: 'Alert queue degraded. Restore the API policy surface to refresh live alerts.',
                })
            )
            if (import.meta.env.DEV) {
                console.error('Failed to load alerts:', err)
            }
        } finally {
            setLoading(false)
        }
    }, [endTime, filterStatus, filterType, minSeverity, startTime])

    useEffect(() => {
        void loadAlerts()
        const interval = setInterval(() => {
            void loadAlerts()
        }, 5000)
        return () => clearInterval(interval)
    }, [loadAlerts])

    useEffect(() => {
        if (!streamMessage || !('type' in streamMessage)) return
        if (streamMessage.type !== 'alert_status_updated') return
        const { alert_id: alertId, status } = streamMessage
        setAlerts((prev) =>
            prev.map((a) => (a.id === alertId ? { ...a, status } : a))
        )
    }, [streamMessage])

    useEffect(() => {
        if (!quickPreset) return
        if (quickPreset === 'clear') {
            setFilterType('')
            setFilterStatus('')
            setMinSeverity(0)
            setStartTime('')
            setEndTime('')
            return
        }
        if (quickPreset === 'critical-new') {
            setFilterType('')
            setFilterStatus('new')
            setMinSeverity(70)
            return
        }
        if (quickPreset === 'high-open') {
            setFilterType('')
            setFilterStatus('')
            setMinSeverity(50)
            return
        }
        if (quickPreset === 'last-hour') {
            const now = new Date()
            const start = new Date(now.getTime() - 60 * 60 * 1000)
            setStartTime(start.toISOString().slice(0, 16))
            setEndTime(now.toISOString().slice(0, 16))
        }
    }, [quickPreset])

    useEffect(() => {
        setActiveAlertIdx((idx) => {
            if (alerts.length === 0) return 0
            return Math.max(0, Math.min(idx, alerts.length - 1))
        })
    }, [alerts.length])

    const handleStatusUpdate = async (alertId: number, status: string, notes?: string) => {
        try {
            await apiClient.updateAlertStatus(alertId, status, notes)
            await loadAlerts()
            setEditingAlert(null)
            setAlertNotes('')
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to update alert status'
            if (import.meta.env.DEV) {
                console.error('Failed to update alert status:', err)
            }
            alert(`Failed to update alert status: ${errorMessage}`)
        }
    }

    const handleExport = async (format: 'csv' | 'json') => {
        const params: AlertFilters = {}
        if (filterType) params.alert_type = filterType
        if (filterStatus) params.status = filterStatus
        if (minSeverity > 0) params.min_severity = minSeverity
        if (startTime) params.start_time = new Date(startTime).toISOString()
        if (endTime) params.end_time = new Date(endTime).toISOString()
        try {
            await apiClient.downloadAlertsExport(format, params)
        } catch (err) {
            const msg = err instanceof Error ? err.message : 'Export failed'
            alert(msg)
        }
    }

    return (
        <div
            className="alerts-panel"
            tabIndex={0}
            onKeyDown={(event) => {
                if (isEditableTarget(event.target) || alerts.length === 0) return
                if (event.key.toLowerCase() === 'j') {
                    event.preventDefault()
                    setActiveAlertIdx((idx) => Math.min(idx + 1, alerts.length - 1))
                    return
                }
                if (event.key.toLowerCase() === 'k') {
                    event.preventDefault()
                    setActiveAlertIdx((idx) => Math.max(idx - 1, 0))
                    return
                }

                const activeAlert = alerts[activeAlertIdx]
                if (!activeAlert) return
                if (event.key.toLowerCase() === 'n') {
                    event.preventDefault()
                    void handleStatusUpdate(activeAlert.id, 'new')
                }
                if (event.key.toLowerCase() === 'r') {
                    event.preventDefault()
                    void handleStatusUpdate(activeAlert.id, 'reviewed')
                }
                if (event.key.toLowerCase() === 's') {
                    event.preventDefault()
                    void handleStatusUpdate(activeAlert.id, 'resolved')
                }
                if (event.key.toLowerCase() === 'f') {
                    event.preventDefault()
                    void handleStatusUpdate(activeAlert.id, 'false_positive')
                }
            }}
            aria-label="Alerts queue"
        >
            <div className="panel-header">
                <div>
                    <h2>Alerts</h2>
                    <div className="panel-subtitle">
                        <span className="label">Integrity</span>: hard physics / data integrity violations.{" "}
                        <span className="label">Suspicious</span>: softer data‑quality or unusual behaviour signals.
                    </div>
                    <div className="panel-subtitle">Queue hotkeys: J/K move, R reviewed, S resolved, F false positive, N new.</div>
                </div>
                <div className="panel-controls">
                    <div className="filter-row">
                        <select
                            value={filterType}
                            onChange={(e) => setFilterType(e.target.value)}
                            className="type-filter"
                        >
                            <option value="">All Types</option>
                            <option value="TELEPORT">Teleport (integrity)</option>
                            <option value="TELEPORT_T2">Teleport (suspicious)</option>
                            <option value="TURN_RATE">Turn rate (integrity)</option>
                            <option value="TURN_RATE_T2">Turn rate (suspicious)</option>
                            <option value="POSITION_INVALID">Position invalid</option>
                            <option value="ACCELERATION">Acceleration / SOG mismatch</option>
                            <option value="HEADING_COG_CONSISTENCY">Heading / COG consistency</option>
                        </select>
                        <select
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value)}
                            className="status-filter"
                        >
                            <option value="">All Statuses</option>
                            <option value="new">New</option>
                            <option value="reviewed">Reviewed</option>
                            <option value="resolved">Resolved</option>
                            <option value="false_positive">False Positive</option>
                        </select>
                        <select
                            value={minSeverity}
                            onChange={(e) => setMinSeverity(Number(e.target.value))}
                            className="severity-filter"
                        >
                            <option value={0}>All Severities</option>
                            <option value={30}>Low (30+)</option>
                            <option value={50}>Medium (50+)</option>
                            <option value={70}>High (70+)</option>
                        </select>
                    </div>
                    <div className="filter-row">
                        <input
                            type="datetime-local"
                            value={startTime}
                            onChange={(e) => setStartTime(e.target.value)}
                            placeholder="Start time"
                            className="time-filter"
                        />
                        <input
                            type="datetime-local"
                            value={endTime}
                            onChange={(e) => setEndTime(e.target.value)}
                            placeholder="End time"
                            className="time-filter"
                        />
                        <button onClick={() => { setStartTime(''); setEndTime('') }} className="btn-clear">
                            Clear Dates
                        </button>
                    </div>
                    <div className="export-buttons">
                        <button onClick={() => handleExport('csv')} className="btn-export">
                            Export CSV
                        </button>
                        <button onClick={() => handleExport('json')} className="btn-export">
                            Export JSON
                        </button>
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="loading">Loading alerts...</div>
            ) : (
                <div className="alerts-list">
                    {loadError ? (
                        <div className="alerts-state alerts-state--error" role="alert">
                            <strong>Queue degraded.</strong>
                            <span>{loadError}</span>
                            <button type="button" className="btn-clear" onClick={() => void loadAlerts()}>
                                Retry sync
                            </button>
                        </div>
                    ) : alerts.length === 0 ? (
                        <div className="alerts-state empty-state">
                            <strong>No alerts found</strong>
                            <span>Adjust queue filters or wait for the next ingest window.</span>
                        </div>
                    ) : (
                        alerts.map((alert, idx) => (
                            <div
                                key={alert.id}
                                className={`alert-card severity-${getSeverityLevel(alert.severity)} ${idx === activeAlertIdx ? 'alert-card--active' : ''}`}
                                onClick={() => setActiveAlertIdx(idx)}
                            >
                                <div className="alert-header">
                                    <div className="alert-type">
                                        {formatAlertType(alert.type)}
                                    </div>
                                    <div className="alert-header-badges">
                                        {alert.evidence?.watchlist_priority ? (
                                            <span
                                                className={`watchlist-tag watchlist-tag-${alert.evidence.watchlist_priority}`}
                                                title="Watchlisted vessel"
                                            >
                                                Watchlist ({alert.evidence.watchlist_priority})
                                            </span>
                                        ) : null}
                                        <div className={`severity-badge severity-${getSeverityLevel(alert.severity)}`}>
                                            {alert.severity}
                                        </div>
                                    </div>
                                </div>
                                <div className="alert-summary">{alert.summary}</div>
                                <div className="alert-details">
                                    <div className="detail-item">
                                        <span className="label">MMSI:</span>
                                        <span>{alert.mmsi}</span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="label">Time:</span>
                                        <span>{new Date(alert.timestamp).toLocaleString()}</span>
                                    </div>
                                </div>
                                <div className="alert-details">
                                    <div className="detail-item">
                                        <span className="label">Class:</span>
                                        <span>{getAlertClassification(alert.type).tierLabel}</span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="label">Status:</span>
                                        <span className={`status-badge status-${alert.status || 'new'}`}>
                                            {alert.status || 'new'}
                                        </span>
                                    </div>
                                </div>
                                {alert.notes && (
                                    <div className="alert-notes">
                                        <strong>Notes:</strong> {alert.notes}
                                    </div>
                                )}
                                {alert.evidence && (
                                    <details className="alert-evidence">
                                        <summary>Evidence</summary>
                                        {renderEvidence(alert)}
                                    </details>
                                )}
                                <div className="alert-actions">
                                    {(linkToAlert || linkToMapForMmsi) && (
                                        <div className="alert-actions-row aml-triage-links">
                                            {linkToAlert ? (
                                                <Link to={linkToAlert(alert.id)} className="btn-aml-triage">
                                                    Investigate
                                                </Link>
                                            ) : null}
                                            {linkToMapForMmsi ? (
                                                <Link to={linkToMapForMmsi(alert.mmsi)} className="btn-aml-triage">
                                                    Map
                                                </Link>
                                            ) : null}
                                        </div>
                                    )}
                                    {editingAlert === alert.id ? (
                                        <div className="status-edit">
                                            <select
                                                value={alert.status || 'new'}
                                                onChange={(e) => handleStatusUpdate(alert.id, e.target.value, alertNotes)}
                                                className="status-select"
                                            >
                                                <option value="new">New</option>
                                                <option value="reviewed">Reviewed</option>
                                                <option value="resolved">Resolved</option>
                                                <option value="false_positive">False Positive</option>
                                            </select>
                                            <input
                                                type="text"
                                                value={alertNotes}
                                                onChange={(e) => setAlertNotes(e.target.value)}
                                                placeholder="Add notes..."
                                                className="notes-input"
                                            />
                                            <button onClick={() => handleStatusUpdate(alert.id, alert.status || 'new', alertNotes)} className="btn-save">
                                                Save
                                            </button>
                                            <button onClick={() => { setEditingAlert(null); setAlertNotes(''); }} className="btn-cancel">
                                                Cancel
                                            </button>
                                        </div>
                                    ) : (
                                        <button onClick={() => { setEditingAlert(alert.id); setAlertNotes(alert.notes || ''); }} className="btn-edit">
                                            Update Status
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}
