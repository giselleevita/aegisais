import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '@/core/api-client'
import type { Incident } from '@/shared/types/common'

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
      const msg = err instanceof Error ? err.message : 'Failed to load incidents'
      setIncidents([])
      // Most common case: unauthenticated user visiting via UI smoke tests.
      setError(
        msg.includes('401') || msg.toLowerCase().includes('not authenticated') || msg.toLowerCase().includes('unauthorized')
          ? 'Sign in to view incidents.'
          : msg
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
      <aside className="aml-incidents__list">
        <div className="aml-incidents__header">
          <h2 className="aml-page-title">Incidents</h2>
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

        {loading ? <p className="aml-incidents__message">Loading incidents...</p> : null}

        {!loading && error ? <p className="aml-incidents__message aml-incidents__message--error" role="alert">{error}</p> : null}

        {!loading && !error ? (
          <ul>
            {incidents.map((incident) => (
              <li key={incident.id}>
                <Link
                  to={`/incidents/${incident.id}`}
                  className="aml-incidents__link"
                >
                  <strong>#{incident.id}</strong> {incident.title}
                  <div className="aml-incidents__status">{incident.status}</div>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}

        {!loading && !error && incidents.length === 0 ? (
          <p className="aml-incidents__message">No incidents found.</p>
        ) : null}
      </aside>

      <section className="aml-incidents__detail">
        <h3>Incident details</h3>
        <p>Open an incident from the list to view provenance and edit status.</p>
      </section>
    </div>
  )
}

