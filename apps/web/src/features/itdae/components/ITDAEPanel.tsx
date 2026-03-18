import { useEffect, useState, type ReactNode } from 'react'
import { useITDAEAlerts } from '@/features/itdae/hooks/useITDAEAlerts'
import type { ItdaeAlert } from '@/features/itdae/types'
import './ITDAEPanel.css'

const RISK_LEVEL_MAP: Record<string, string> = {
    GEOFENCE_ENTRY: 'Zone Entry',
    LOITER_IN_ZONE: 'Loitering',
    AIS_DARK_IN_ZONE: 'AIS Dark',
    SLOW_TRANSIT_ZONE: 'Slow Transit',
}

const ZONE_RISK_COLOURS: Record<string, string> = {
    critical: 'var(--itdae-critical)',
    high: 'var(--itdae-high)',
    medium: 'var(--itdae-medium)',
}

function getSeverityClass(severity: number): string {
    if (severity >= 70) return 'sev-high'
    if (severity >= 45) return 'sev-medium'
    return 'sev-low'
}

function formatAlertType(type: string): string {
    return RISK_LEVEL_MAP[type] ?? type
}

function formatTime(iso: string): string {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function EvidenceRow({ label, value }: { label: string; value: ReactNode }) {
    return (
        <div className="itdae-evidence-row">
            <span className="itdae-ev-label">{label}</span>
            <span className="itdae-ev-value">{value}</span>
        </div>
    )
}

function AlertEvidence({ alert }: { alert: ItdaeAlert }) {
    const e = alert.evidence
    const zoneRisk = e.zone_risk_level as string | undefined

    return (
        <div className="itdae-evidence">
            {e.zone_name && (
                <EvidenceRow
                    label="Zone"
                    value={
                        <span style={{ color: zoneRisk ? ZONE_RISK_COLOURS[zoneRisk] : undefined }}>
                            {e.zone_name} ({e.zone_risk_level})
                        </span>
                    }
                />
            )}
            {e.duration_min != null && (
                <EvidenceRow label="Loiter duration" value={`${e.duration_min.toFixed(0)} min`} />
            )}
            {e.gap_sec != null && (
                <EvidenceRow label="Dark gap" value={
                    e.gap_sec >= 3600
                        ? `${(e.gap_sec / 3600).toFixed(1)} hr`
                        : `${(e.gap_sec / 60).toFixed(0)} min`
                } />
            )}
            {e.implied_speed_kn != null && (
                <EvidenceRow label="Speed" value={`${e.implied_speed_kn.toFixed(1)} kn`} />
            )}
            {e.sog_kn != null && (
                <EvidenceRow label="SOG" value={`${e.sog_kn.toFixed(1)} kn`} />
            )}
            {e.lat != null && e.lon != null && (
                <EvidenceRow label="Position" value={`${e.lat.toFixed(4)}, ${e.lon.toFixed(4)}`} />
            )}
        </div>
    )
}

export default function ITDAEPanel() {
    const { alerts, connected, unreadCount, clearUnread } = useITDAEAlerts()
    const [expanded, setExpanded] = useState<number | null>(null)
    const [filterType, setFilterType] = useState('')

    // Clear unread badge when panel is opened/viewed
    useEffect(() => {
        clearUnread()
    }, [clearUnread])

    const visible = filterType
        ? alerts.filter((a) => a.type === filterType)
        : alerts

    return (
        <div className="itdae-panel">
            {/* ── Header ─────────────────────────────────────────────────── */}
            <div className="itdae-header">
                <div className="itdae-title-row">
                    <h2 className="itdae-title">
                        Infrastructure Threat
                        {unreadCount > 0 && (
                            <span className="itdae-badge">{unreadCount}</span>
                        )}
                    </h2>
                    <div className={`itdae-stream-dot ${connected ? 'connected' : 'disconnected'}`}
                        title={connected ? 'Stream connected' : 'Stream disconnected'} />
                </div>
                <p className="itdae-subtitle">
                    Baltic cable corridor threat detection — real-time ITDAE alerts
                </p>

                {/* Filter bar */}
                <div className="itdae-filters">
                    <select
                        value={filterType}
                        onChange={(e) => setFilterType(e.target.value)}
                        className="itdae-select"
                        id="itdae-type-filter"
                        title="Filter by alert type"
                    >
                        <option value="">All types</option>
                        <option value="GEOFENCE_ENTRY">Zone Entry</option>
                        <option value="LOITER_IN_ZONE">Loitering</option>
                        <option value="AIS_DARK_IN_ZONE">AIS Dark</option>
                        <option value="SLOW_TRANSIT_ZONE">Slow Transit</option>
                    </select>
                    <span className="itdae-count">{visible.length} alerts</span>
                </div>
            </div>

            {/* ── Alert list ─────────────────────────────────────────────── */}
            <div className="itdae-list">
                {visible.length === 0 ? (
                    <div className="itdae-empty">
                        {connected ? 'No ITDAE alerts — monitoring active' : 'Connecting to stream…'}
                    </div>
                ) : (
                    visible.map((alert, idx) => (
                        <div
                            key={`${alert.id ?? idx}-${alert.timestamp}`}
                            className={`itdae-card ${getSeverityClass(alert.severity)}`}
                            onClick={() => setExpanded(expanded === idx ? null : idx)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => e.key === 'Enter' && setExpanded(expanded === idx ? null : idx)}
                            id={`itdae-alert-${alert.id ?? idx}`}
                        >
                            <div className="itdae-card-header">
                                <div className="itdae-card-left">
                                    <span className="itdae-type-tag">{formatAlertType(alert.type)}</span>
                                    <span className="itdae-mmsi">{alert.mmsi}</span>
                                </div>
                                <div className="itdae-card-right">
                                    <span className={`itdae-sev ${getSeverityClass(alert.severity)}`}>
                                        {alert.severity}
                                    </span>
                                    <span className="itdae-time">{formatTime(alert.timestamp)}</span>
                                </div>
                            </div>

                            <p className="itdae-summary">{alert.summary}</p>

                            {expanded === idx && (
                                <AlertEvidence alert={alert} />
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    )
}
