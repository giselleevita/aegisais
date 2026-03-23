import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '@/core/api-client'
import type { Incident } from '@/shared/types/common'

const STATUS_OPTIONS = ['open', 'triaged', 'investigating', 'resolved', 'dismissed']

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
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
  }

  useEffect(() => {
    void load()
  }, [statusFilter])

  return (
    <div className="aml-page-pad aml-incidents">
      <aside className="aml-incidents__list">
        <div className="aml-incidents__header">
          <h2 className="aml-page-title">Incidents</h2>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        {loading ? <p>Loading incidents...</p> : null}

        {!loading && error ? <p>{error}</p> : null}

        {!loading && !error ? (
          <ul>
            {incidents.map((incident) => (
              <li key={incident.id}>
                <Link
                  to={`/incidents/${incident.id}`}
                  style={{
                    display: 'block',
                    padding: '0.65rem 0.75rem',
                    textDecoration: 'none',
                    color: 'inherit',
                  }}
                >
                  <strong>#{incident.id}</strong> {incident.title}
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{incident.status}</div>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}

        {!loading && !error && incidents.length === 0 ? <p>No incidents found.</p> : null}
      </aside>

      <section className="aml-incidents__detail">
        <h3>Incident details</h3>
        <p>Open an incident from the list to view provenance and edit status.</p>
      </section>
    </div>
  )
}

