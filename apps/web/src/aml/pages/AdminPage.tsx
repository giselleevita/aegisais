import { useEffect, useState } from 'react'
import { apiClient } from '@/core/api-client'
import type { IntegrationFeed, IntegrationFeedStatus } from '@/shared/types/common'

const FALLBACK_FEEDS: IntegrationFeed[] = [
  { id: 'satellite_ais', label: 'Satellite AIS', status: 'disconnected', detail: null },
  { id: 'sar_eo', label: 'SAR / EO', status: 'disconnected', detail: null },
  { id: 'rf_sigint', label: 'RF (SIGINT)', status: 'disconnected', detail: null },
]

function statusLabel(status: IntegrationFeedStatus): string {
  switch (status) {
    case 'ready':
      return 'Ready'
    case 'partial':
      return 'Partial'
    case 'error':
      return 'Error'
    default:
      return 'Not connected'
  }
}

function statusClass(status: IntegrationFeedStatus): string {
  switch (status) {
    case 'ready':
      return 'aml-feed-stubs__status--ready'
    case 'partial':
      return 'aml-feed-stubs__status--partial'
    case 'error':
      return 'aml-feed-stubs__status--error'
    default:
      return 'aml-feed-stubs__status--off'
  }
}

export default function AdminPage() {
  const [feeds, setFeeds] = useState<IntegrationFeed[]>(FALLBACK_FEEDS)
  const [loading, setLoading] = useState(true)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await apiClient.getIntegrationFeeds()
        if (!cancelled) {
          setFeeds(data.feeds)
          setFromApi(true)
        }
      } catch {
        if (!cancelled) {
          setFeeds(FALLBACK_FEEDS)
          setFromApi(false)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="aml-page-pad">
      <h2 className="aml-page-title">Admin &amp; control plane</h2>
      <div className="aml-admin-stub">
        Zones, rules, org, and user management will live here. Server-side authorization is required
        before exposing destructive actions; this route is a layout placeholder for that program of work.
      </div>

      <h3 className="aml-admin-subtitle">External feeds</h3>
      <p className="aml-admin-lead">
        Live status from <code className="aml-admin-code">GET /v1/integrations/feeds</code> when you are
        signed in (viewer role or above). AML integrates partner sensors; it does not own them.
      </p>
      {!fromApi && !loading ? (
        <p className="aml-admin-hint">Using offline defaults — sign in to load feed status from the API.</p>
      ) : null}
      {loading ? <p className="aml-admin-hint">Loading feed status…</p> : null}

      <ul className="aml-feed-stubs" aria-label="Optional feed integrations">
        {feeds.map((f) => (
          <li key={f.id}>
            <span className="aml-feed-stubs__name">{f.label}</span>
            <span className={`aml-feed-stubs__status ${statusClass(f.status)}`}>
              {statusLabel(f.status)}
            </span>
          </li>
        ))}
      </ul>
      {feeds.some((f) => f.detail) ? (
        <dl className="aml-feed-details">
          {feeds
            .filter((f) => f.detail)
            .map((f) => (
              <div key={f.id}>
                <dt>{f.label}</dt>
                <dd>{f.detail}</dd>
              </div>
            ))}
        </dl>
      ) : null}
    </div>
  )
}
