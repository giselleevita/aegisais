import { useSearchParams } from 'react-router-dom'
import MapView from '@/features/map/components/MapView'
import VesselDetails from '@/features/vessels/components/VesselDetails'

export default function MapPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const mmsi = searchParams.get('mmsi')

  return (
    <div className="aml-map-page">
      <div className="aml-map-page__map">
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
        <div className="aml-map-page__details">
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
    </div>
  )
}
