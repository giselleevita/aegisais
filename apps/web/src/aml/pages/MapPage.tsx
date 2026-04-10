import { useSearchParams } from 'react-router-dom'
import MapView from '@/features/map/components/MapView'
import VesselDetails from '@/features/vessels/components/VesselDetails'
import { AML_QUERY } from '@/aml/amlRoutes'

export default function MapPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const mmsi = searchParams.get(AML_QUERY.mmsi)

  return (
    <div className="aml-map-page">
      <div className="aml-map-page__map">
        <MapView
          selectedVessel={mmsi}
          onVesselClick={(nextMmsi) => {
            const next = new URLSearchParams(searchParams)
            next.set(AML_QUERY.mmsi, nextMmsi)
            setSearchParams(next)
          }}
          showInfrastructure
        />
      </div>
      {mmsi ? (
        <div className="aml-map-page__details">
          <VesselDetails
            mmsi={mmsi}
            onClose={() => {
              const next = new URLSearchParams(searchParams)
              next.delete(AML_QUERY.mmsi)
              setSearchParams(next)
            }}
          />
        </div>
      ) : null}
    </div>
  )
}
