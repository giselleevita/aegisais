import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '@/core/api-client'
import { describeApiFailure } from '@/core/api-errors'
import type { Incident } from '@/shared/types/common'
import { getIncidentDetailPath } from '@/aml/amlRoutes'

const STATUS_OPTIONS = ['open', 'triaged', 'investigating', 'resolved', 'dismissed']

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const rows = await apiClient.getIncidents({
        status: statusFilter || undefined,
        limit: 200,
      })
      setIncidents(rows)
    } catch (err) {
      setIncidents([])
      setError(
        describeApiFailure(err, {
          fallback: 'Unable to load incidents.',
          unauthorized: 'Sign in to view incidents.',
          offline: 'Incident registry unavailable while the API policy surface is offline.',
        })
      )
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="aml-page-pad aml-incidents">
      <section className="aml-incidents__hero">
        <div>
          <span className="aml-operations__eyebrow">Governance</span>
          <h2 className="aml-page-title">Incident registry</h2>
          <p className="aml-incidents__lead">
            Track cross-alert cases, preserve incident evidence, and move incidents through triage and disposition without losing provenance.
          </p>
        </div>
        <div className="aml-incidents__hero-card">
          <span>Status filter</span>
          <label className="sr-only" htmlFor="incidents-status-filter">Filter incidents by status</label>
          <select
            id="incidents-status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter incidents by status"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
      </section>

      <div className="aml-incidents__workspace">
        <aside className="aml-incidents__list">
          <div className="aml-incidents__header">
            <h3>Case queue</h3>
          </div>

          {loading ? <p className="aml-incidents__message">Loading incidents...</p> : null}

          {!loading && error ? <p className="aml-incidents__message aml-incidents__message--error" role="alert">{error}</p> : null}

          {!loading && !error ? (
            <ul>
              {incidents.map((incident) => (
                <li key={incident.id}>
                  <Link
                    to={getIncidentDetailPath(incident.id)}
                    className="aml-incidents__link"
                    aria-label={`#${incident.id} ${incident.title}`}
                  >
                    <div className="aml-incidents__link-top">
                      <strong>#{incident.id}</strong>
                      <div className="aml-incidents__status">{incident.status}</div>
                    </div>
                    <div className="aml-incidents__title">{incident.title}</div>
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}

          {!loading && !error && incidents.length === 0 ? (
            <p className="aml-incidents__message">No incidents found.</p>
          ) : null}
        </aside>

        <section className="aml-incidents__detail aml-incidents__detail--idle">
          <span className="aml-operations__eyebrow">Detail view</span>
          <h3>Incident details</h3>
          <p>Open an incident from the list to inspect case artifacts, review activity, and update disposition.</p>
        </section>
      </div>
    </div>
  )
}

