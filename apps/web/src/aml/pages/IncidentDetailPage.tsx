import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { apiClient } from '@/core/api-client'
import type { AuditLogEntry, Incident } from '@/shared/types/common'

const STATUS_OPTIONS = ['open', 'triaged', 'investigating', 'resolved', 'dismissed']

export default function IncidentDetailPage() {
  const { incidentId } = useParams()
  const navigate = useNavigate()
  const id = Number(incidentId)

  const [incident, setIncident] = useState<Incident | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [titleDraft, setTitleDraft] = useState('')
  const [statusDraft, setStatusDraft] = useState('open')
  const [saving, setSaving] = useState(false)
  const [timeline, setTimeline] = useState<AuditLogEntry[]>([])
  const [timelineLoading, setTimelineLoading] = useState(false)

  useEffect(() => {
    if (!Number.isFinite(id)) return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const row = await apiClient.getIncident(id)
        if (cancelled) return
        setIncident(row)
        setTitleDraft(row.title)
        setStatusDraft(row.status)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to load incident'
        if (cancelled) return
        setIncident(null)
        setError(
          msg.includes('401') ||
            msg.toLowerCase().includes('not authenticated') ||
            msg.toLowerCase().includes('unauthorized')
            ? 'Sign in to view incidents.'
            : msg
        )
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    if (!Number.isFinite(id)) return
    let cancelled = false
    ;(async () => {
      setTimelineLoading(true)
      try {
        const rows = await apiClient.getAuditLogs({
          resource_type: 'incident',
          resource_id: String(id),
          limit: 100,
        })
        if (!cancelled) setTimeline(rows)
      } catch {
        if (!cancelled) setTimeline([])
      } finally {
        if (!cancelled) setTimelineLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, incident?.status, incident?.title])

  const handleSave = async () => {
    if (!incident) return
    setSaving(true)
    setError(null)
    try {
      const updated = await apiClient.updateIncident(incident.id, {
        status: statusDraft,
        title: titleDraft,
      })
      setIncident(updated)
      navigate(`/incidents/${updated.id}`, { replace: true })
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update incident'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  if (!Number.isFinite(id)) {
    return (
      <div className="aml-page-pad">
        <p>Invalid incident id.</p>
        <Link to="/incidents">Back to incidents</Link>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="aml-page-pad">
        <p>Loading incident...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="aml-page-pad">
        <p>{error}</p>
        <Link to="/incidents">Back to incidents</Link>
      </div>
    )
  }

  if (!incident) {
    return (
      <div className="aml-page-pad">
        <p>Incident not found.</p>
        <Link to="/incidents">Back to incidents</Link>
      </div>
    )
  }

  return (
    <div className="aml-page-pad">
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'baseline' }}>
        <h2 style={{ margin: 0 }}>Incident #{incident.id}</h2>
        <Link to="/incidents">Back to incidents</Link>
      </div>

      <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: '1fr', gap: '1rem' }}>
        <section style={{ border: '1px solid var(--border-default)', borderRadius: 8, padding: '1rem', background: 'var(--bg-surface)' }}>
          <h3 style={{ marginTop: 0 }}>Disposition</h3>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '0.75rem' }}>
            Title
            <input value={titleDraft} onChange={(e) => setTitleDraft(e.target.value)} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '0.75rem' }}>
            Status
            <select value={statusDraft} onChange={(e) => setStatusDraft(e.target.value)}>
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => void handleSave()} disabled={saving}>
            {saving ? 'Saving...' : 'Save incident'}
          </button>
          {incident.status !== statusDraft ? <div style={{ marginTop: '0.5rem', color: 'var(--text-secondary)' }}>Unsaved changes.</div> : null}
        </section>

        <section style={{ border: '1px solid var(--border-default)', borderRadius: 8, padding: '1rem', background: 'var(--bg-surface)' }}>
          <h3 style={{ marginTop: 0 }}>Evidence bundle</h3>
          <pre style={{ margin: 0, maxHeight: '50vh', overflow: 'auto' }}>{JSON.stringify(incident.evidence_bundle, null, 2)}</pre>
        </section>

        <section style={{ border: '1px solid var(--border-default)', borderRadius: 8, padding: '1rem', background: 'var(--bg-surface)' }}>
          <h3 style={{ marginTop: 0 }}>Activity timeline</h3>
          {timelineLoading ? <p>Loading activity...</p> : null}
          {!timelineLoading && timeline.length === 0 ? <p>No activity rows found.</p> : null}
          {!timelineLoading && timeline.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
              {timeline.map((row) => (
                <li key={row.id} style={{ marginBottom: '0.45rem' }}>
                  <strong>{row.action}</strong> - {new Date(row.timestamp).toLocaleString()}
                  <div style={{ color: 'var(--text-secondary)' }}>{row.change_summary}</div>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </div>
  )
}

