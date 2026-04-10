import { useState } from 'react'
import { useOutletContext, useSearchParams } from 'react-router-dom'
import MapView from '@/features/map/components/MapView'
import VesselDetails from '@/features/vessels/components/VesselDetails'
import AlertsPanel from '@/features/alerts/components/AlertsPanel'
import ErrorBoundary from '@/shared/components/ErrorBoundary'
import ReplayControls from '@/shared/components/ReplayControls/ReplayControls'
import type { AmlOutletContext } from '@/aml/amlOutletContext'
import { getAlertDetailPath, getMapForMmsiPath, AML_QUERY } from '@/aml/amlRoutes'

const RECENT_VESSELS_STORAGE_KEY = 'aegisais_recent_vessels'

function readRecentVessels(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_VESSELS_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed.filter((x): x is string => typeof x === 'string').slice(0, 6)
  } catch {
    return []
  }
}

export default function OperationsPage() {
  const { lastMessage, authContext } = useOutletContext<AmlOutletContext>()
  const [searchParams, setSearchParams] = useSearchParams()
  const mmsi = searchParams.get(AML_QUERY.mmsi)
  const [quickPreset, setQuickPreset] = useState<'critical-new' | 'high-open' | 'last-hour' | 'clear' | null>(null)
  const [recentVessels, setRecentVessels] = useState<string[]>(() => readRecentVessels())
  const streamStateLabel = lastMessage ? 'Recent event received' : 'Awaiting live event'
  const postureLabel = authContext?.claims.clearances[0] ?? 'UNCLASSIFIED'
  const releaseLabel = authContext?.claims.releasability[0] ?? 'none'

  const pushRecentVessel = (nextMmsi: string) => {
    setRecentVessels((prev) => {
      const deduped = [nextMmsi, ...prev.filter((x) => x !== nextMmsi)].slice(0, 6)
      try {
        localStorage.setItem(RECENT_VESSELS_STORAGE_KEY, JSON.stringify(deduped))
      } catch {
        // ignore
      }
      return deduped
    })
  }

  return (
    <div className="aml-operations">
      <section className="aml-operations__brief">
        <div className="aml-operations__brief-copy">
          <span className="aml-operations__eyebrow">Operations</span>
          <h2>Priority queue and surface picture</h2>
          <p>
            Hold the ranked anomaly queue, keep the live surface view in frame, and pivot directly into alert, vessel, and incident work without leaving the deck.
          </p>
        </div>
        <div className="aml-operations__brief-cards">
          <article>
            <span>Feed state</span>
            <strong>{streamStateLabel}</strong>
          </article>
          <article>
            <span>Clearance</span>
            <strong>{postureLabel}</strong>
          </article>
          <article>
            <span>Releasability</span>
            <strong>{releaseLabel}</strong>
          </article>
          <article>
            <span>Focus</span>
            <strong>{mmsi ? `Vessel ${mmsi}` : 'Queue scanning'}</strong>
          </article>
        </div>
      </section>

      <div className="aml-operations__workspace">
        <aside className="aml-operations__queue">
          <section className="aml-operations__quick" aria-label="Triage quick actions">
            <div className="aml-operations__quick-head">
              <div>
                <span className="aml-operations__eyebrow">Quick actions</span>
                <h3>Triage accelerators</h3>
              </div>
              <p>Drive the queue by urgency, recency, and current vessel focus.</p>
            </div>
            <div className="aml-operations__quick-actions">
              <button type="button" onClick={() => setQuickPreset('critical-new')}>Critical new</button>
              <button type="button" onClick={() => setQuickPreset('high-open')}>High and above</button>
              <button type="button" onClick={() => setQuickPreset('last-hour')}>Last hour</button>
              <button type="button" onClick={() => setQuickPreset('clear')}>Clear filters</button>
            </div>
            {recentVessels.length > 0 ? (
              <div className="aml-operations__recent">
                <span>Recent vessels</span>
                <div>
                  {recentVessels.map((recent) => (
                    <button
                      key={recent}
                      type="button"
                      onClick={() => {
                        const next = new URLSearchParams(searchParams)
                        next.set(AML_QUERY.mmsi, recent)
                        setSearchParams(next)
                      }}
                    >
                      {recent}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </section>
          <details className="aml-operations__ingest">
            <summary>Data upload &amp; replay</summary>
            <div className="aml-operations__ingest-body">
              <ErrorBoundary>
                <ReplayControls lastMessage={lastMessage} />
              </ErrorBoundary>
            </div>
          </details>
          <AlertsPanel
            streamMessage={lastMessage}
            linkToAlert={(id) => getAlertDetailPath(id)}
            linkToMapForMmsi={(m) => getMapForMmsiPath(m)}
            quickPreset={quickPreset}
          />
        </aside>

        <section className="aml-operations__right">
          <div className="aml-operations__map-stage">
            <div className="aml-operations__map-brief">
              <div>
                <span className="aml-operations__eyebrow">Surface picture</span>
                <h3>{mmsi ? `Tracking vessel ${mmsi}` : 'Maintain operating picture'}</h3>
              </div>
              <p>{mmsi ? 'Correlate vessel behavior with alerts and route evidence.' : 'Select a vessel from the map or queue to open a focused investigation pane.'}</p>
            </div>
            <div className="aml-operations__map">
              <MapView
                selectedVessel={mmsi}
                onVesselClick={(nextMmsi) => {
                  const next = new URLSearchParams(searchParams)
                  next.set(AML_QUERY.mmsi, nextMmsi)
                  setSearchParams(next)
                  pushRecentVessel(nextMmsi)
                }}
                showInfrastructure
              />
            </div>
          </div>
          {mmsi ? (
            <div className="aml-operations__vessel">
              <VesselDetails
                mmsi={mmsi}
                onClose={() => {
                  const next = new URLSearchParams(searchParams)
                  next.delete(AML_QUERY.mmsi)
                  setSearchParams(next)
                }}
              />
            </div>
          ) : (
            <div className="aml-operations__vessel aml-operations__vessel--idle">
              <span className="aml-operations__eyebrow">Focus target</span>
              <h3>No vessel pinned</h3>
              <p>Choose a vessel from the queue or map to open identity, watchlist, and movement context here.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
