import { useEffect, useState } from 'react'
import { apiClient } from '@/core/api-client'
import type { AnomalyModelStatus, FestivalScenarioStatus, IntegrationFeed, IntegrationFeedStatus } from '@/shared/types/common'

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
    case 'unavailable':
      return 'Unavailable'
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
  const [modelStatus, setModelStatus] = useState<AnomalyModelStatus | null>(null)
  const [scenario, setScenario] = useState<FestivalScenarioStatus | null>(null)
  const [scenarioError, setScenarioError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [data, model, demo] = await Promise.all([
          apiClient.getIntegrationFeeds(),
          apiClient.getAnomalyModelStatus(),
          apiClient.getFestivalScenarioStatus().catch(() => null),
        ])
        if (!cancelled) {
          setFeeds(data.feeds)
          setModelStatus(model)
          setScenario(demo)
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

  useEffect(() => {
    if (!scenario || !['starting', 'running'].includes(scenario.state)) return
    const timer = window.setInterval(() => {
      void apiClient.getFestivalScenarioStatus().then(setScenario).catch(() => undefined)
    }, 1000)
    return () => window.clearInterval(timer)
  }, [scenario])

  const startScenario = async () => {
    try {
      setScenarioError(null)
      setScenario(await apiClient.startFestivalScenario(20))
    } catch (error) {
      setScenarioError(error instanceof Error ? error.message : 'Unable to start scenario')
    }
  }

  const resetScenario = async () => {
    try {
      setScenarioError(null)
      setScenario(await apiClient.resetFestivalScenario())
    } catch (error) {
      setScenarioError(error instanceof Error ? error.message : 'Unable to reset scenario')
    }
  }

  return (
    <div className="aml-page-pad aml-admin">
      <header className="aml-admin__hero">
        <div>
          <span className="aml-operations__eyebrow">Control plane</span>
          <h2 className="aml-page-title">Admin &amp; control plane</h2>
          <p className="aml-admin-lead">
            Coordinate organization-level controls, inspect partner feed readiness, and keep destructive actions gated behind server-side authorization.
          </p>
        </div>
      </header>

      <div className="aml-admin-stub aml-demo-control">
        <div>
          <strong>Berlin festival scenario</strong>
          <p>Replay AIS approach, cable-zone loitering, AIS silence, and an independent SAR detection.</p>
          <small>
            State: {scenario?.state || 'unavailable'} · {scenario?.emitted || 0}/{scenario?.total || 0} observations · {scenario?.fusionAlerts || 0} fused alerts
          </small>
        </div>
        <div className="aml-demo-control__actions">
          <button type="button" onClick={() => void startScenario()} disabled={scenario?.state === 'running'}>Start 3-minute demo</button>
          <button type="button" onClick={() => void resetScenario()}>Reset</button>
        </div>
        {scenarioError ? <p role="alert" className="aml-admin-hint">{scenarioError}</p> : null}
      </div>

      <div className="aml-admin-stub">
        <strong>Anomaly baseline:</strong>{' '}
        {modelStatus?.state || 'unavailable'}
        {modelStatus?.model_version ? ` · ${modelStatus.model_version}` : ''}
        {modelStatus?.reason ? ` · ${modelStatus.reason}` : ''}
        <p>The score is an empirical anomaly percentile, never a probability. Rules remain active if the model is degraded.</p>
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
            {f.lastObservedAt ? <small>Last observation {new Date(f.lastObservedAt).toLocaleString()}</small> : null}
            {typeof f.recordCount === 'number' ? <small>{f.recordCount} observations · {f.mode || 'unknown mode'}</small> : null}
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
