import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { apiClient } from '@/core/api-client'
import { describeApiFailure } from '@/core/api-errors'
import type { AuditLogEntry, Incident } from '@/shared/types/common'
import { AML_PATHS, getIncidentDetailPath } from '@/aml/amlRoutes'

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
        if (cancelled) return
        setIncident(null)
        setError(
          describeApiFailure(err, {
            fallback: 'Unable to load incident.',
            unauthorized: 'Sign in to view incidents.',
            offline: 'Incident detail unavailable while the API policy surface is offline.',
          })
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
      navigate(getIncidentDetailPath(updated.id), { replace: true })
    } catch (err) {
      setError(
        describeApiFailure(err, {
          fallback: 'Unable to update incident.',
          unauthorized: 'Sign in to update incidents.',
          offline: 'Incident updates are unavailable while the API policy surface is offline.',
        })
      )
    } finally {
      setSaving(false)
    }
  }

  if (!Number.isFinite(id)) {
    return (
      <div className="aml-page-pad aml-incident-detail">
        <div className="aml-incident-detail__state aml-incident-detail__state--error">
          <p>Invalid incident id.</p>
        <Link to={AML_PATHS.incidents}>Back to incidents</Link>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="aml-page-pad aml-incident-detail">
        <div className="aml-incident-detail__state">
          <p>Loading incident...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="aml-page-pad aml-incident-detail">
        <div className="aml-incident-detail__state aml-incident-detail__state--error">
          <p>{error}</p>
        <Link to={AML_PATHS.incidents}>Back to incidents</Link>
        </div>
      </div>
    )
  }

  if (!incident) {
    return (
      <div className="aml-page-pad aml-incident-detail">
        <div className="aml-incident-detail__state">
          <p>Incident not found.</p>
        <Link to={AML_PATHS.incidents}>Back to incidents</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="aml-page-pad aml-incident-detail">
      <header className="aml-incident-detail__hero">
        <div>
          <span className="aml-operations__eyebrow">Incident</span>
          <h2 className="aml-page-title">Incident #{incident.id}</h2>
          <p className="aml-incidents__lead">Manage case disposition, preserve incident evidence, and review the audited timeline for this incident.</p>
        </div>
        <Link to={AML_PATHS.incidents} className="aml-incidents__hero-link">Back to incidents</Link>
      </header>

      <div className="aml-incident-detail__workspace">
        <section className="aml-incident-detail__panel">
          <h3>Disposition</h3>
          <label className="aml-incident-detail__field">
            <span>Title</span>
            <input value={titleDraft} onChange={(e) => setTitleDraft(e.target.value)} />
          </label>
          <label className="aml-incident-detail__field">
            <span>Status</span>
            <select value={statusDraft} onChange={(e) => setStatusDraft(e.target.value)}>
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="aml-incident-detail__save" onClick={() => void handleSave()} disabled={saving}>
            {saving ? 'Saving...' : 'Save incident'}
          </button>
          {incident.status !== statusDraft ? <div className="aml-incident-detail__hint">Unsaved changes.</div> : null}
        </section>

        <section className="aml-incident-detail__panel aml-incident-detail__panel--wide">
          <h3>Evidence bundle</h3>
          <pre className="aml-incident-detail__evidence">{JSON.stringify(incident.evidence_bundle, null, 2)}</pre>
        </section>

        <section className="aml-incident-detail__panel aml-incident-detail__panel--wide">
          <h3>Activity timeline</h3>
          {timelineLoading ? <p>Loading activity...</p> : null}
          {!timelineLoading && timeline.length === 0 ? <p>No activity rows found.</p> : null}
          {!timelineLoading && timeline.length > 0 ? (
            <ul className="aml-incident-detail__timeline">
              {timeline.map((row) => (
                <li key={row.id}>
                  <strong>{row.action}</strong> - {new Date(row.timestamp).toLocaleString()}
                  <div>{row.change_summary}</div>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </div>
  )
}

