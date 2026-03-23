import { useOutletContext, useSearchParams } from 'react-router-dom'
import MapView from '@/features/map/components/MapView'
import VesselDetails from '@/features/vessels/components/VesselDetails'
import AlertsPanel from '@/features/alerts/components/AlertsPanel'
import ErrorBoundary from '@/shared/components/ErrorBoundary'
import ReplayControls from '@/shared/components/ReplayControls/ReplayControls'
import type { AmlOutletContext } from '@/aml/amlOutletContext'
import { AML_OPERATIONS_PATH } from '@/aml/amlRoutes'

export default function OperationsPage() {
  const { lastMessage } = useOutletContext<AmlOutletContext>()
  const [searchParams, setSearchParams] = useSearchParams()
  const mmsi = searchParams.get('mmsi')

  return (
    <div className="aml-operations">
      <aside className="aml-operations__queue">
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
          linkToAlert={(id) => `/alerts/${id}`}
          linkToMapForMmsi={(m) => `${AML_OPERATIONS_PATH}?mmsi=${encodeURIComponent(m)}`}
        />
      </aside>
      <section className="aml-operations__right">
        <div className="aml-operations__map">
          <MapView
            selectedVessel={mmsi}
            onVesselClick={(nextMmsi) => {
              const next = new URLSearchParams(searchParams)
              next.set('mmsi', nextMmsi)
              setSearchParams(next)
            }}
            showInfrastructure
          />
        </div>
        {mmsi ? (
          <div className="aml-operations__vessel">
            <VesselDetails
              mmsi={mmsi}
              onClose={() => {
                const next = new URLSearchParams(searchParams)
                next.delete('mmsi')
                setSearchParams(next)
              }}
            />
          </div>
        ) : null}
      </section>
    </div>
  )
}
