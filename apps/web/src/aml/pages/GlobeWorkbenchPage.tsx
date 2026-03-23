import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Cartesian3,
  ClockRange,
  ClockStep,
  Color,
  HeadingPitchRange,
  HeightReference,
  PolylineDashMaterialProperty,
  VerticalOrigin,
  Viewer,
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import type { LayerDefinition } from '@/shared/types/common'
import {
  getFlightsLiveSnapshot,
  getLayerCatalogue,
  getPortsReference,
  getSubseaCables,
  subscribeFlightsLive,
  type CableSegment,
  type FlightPoint,
  type PortPoint,
} from '@/features/globe/globeData'
import './globe-workbench.css'

type TimelineMode = 'live' | 'replay'
type FocusPresetId = 'global' | 'atlantic' | 'indo-pacific' | 'europe-med'

const FOCUS_PRESETS: Record<
  FocusPresetId,
  { label: string; destination: Cartesian3; range: number }
> = {
  global: {
    label: 'Global',
    destination: Cartesian3.fromDegrees(8, 18, 23_000_000),
    range: 11_000_000,
  },
  atlantic: {
    label: 'Atlantic',
    destination: Cartesian3.fromDegrees(-35, 36, 9_000_000),
    range: 5_500_000,
  },
  'indo-pacific': {
    label: 'Indo-Pacific',
    destination: Cartesian3.fromDegrees(112, 9, 12_000_000),
    range: 6_500_000,
  },
  'europe-med': {
    label: 'Europe / Med',
    destination: Cartesian3.fromDegrees(17, 42, 7_500_000),
    range: 4_200_000,
  },
}

export default function GlobeWorkbenchPage() {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<Viewer | null>(null)

  const [timelineMode, setTimelineMode] = useState<TimelineMode>('live')
  const [catalogue, setCatalogue] = useState<LayerDefinition[]>([])
  const [enabled, setEnabled] = useState<Record<string, boolean>>({})
  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(null)
  const [activePreset, setActivePreset] = useState<FocusPresetId>('global')
  const [flights, setFlights] = useState<FlightPoint[]>([])
  const [ports, setPorts] = useState<PortPoint[]>([])
  const [cables, setCables] = useState<CableSegment[]>([])

  const selectedLayer = useMemo(
    () => catalogue.find((layer) => layer.id === selectedLayerId) ?? null,
    [catalogue, selectedLayerId]
  )

  useEffect(() => {
    let cancelled = false
    getLayerCatalogue().then((rows) => {
      if (cancelled) return
      setCatalogue(rows)
      setSelectedLayerId(rows[0]?.id ?? null)
      const nextEnabled: Record<string, boolean> = {}
      rows.forEach((layer) => {
        nextEnabled[layer.id] = layer.enabledByDefault ?? true
      })
      setEnabled(nextEnabled)
    })
    void getPortsReference().then((rows) => !cancelled && setPorts(rows))
    void getSubseaCables().then((rows) => !cancelled && setCables(rows))
    return () => {
      cancelled = true
    }
  }, [])

  const moveCameraToPreset = (presetId: FocusPresetId) => {
    const viewer = viewerRef.current
    if (!viewer) return
    const preset = FOCUS_PRESETS[presetId]
    setActivePreset(presetId)
    viewer.camera.flyTo({
      destination: preset.destination,
      duration: 0.9,
      orientation: {
        heading: 0,
        pitch: -0.95,
        roll: 0,
      },
    })
  }

  const focusOnVisibleEntities = () => {
    const viewer = viewerRef.current
    if (!viewer) return
    void viewer.flyTo(viewer.entities.values, {
      duration: 0.9,
      offset: new HeadingPitchRange(0, -0.9, 3_000_000),
    })
  }

  useEffect(() => {
    let stop: () => void = () => {}
    if (!enabled['flights-live']) return
    if (timelineMode === 'live') {
      void getFlightsLiveSnapshot().then(setFlights)
      stop = subscribeFlightsLive(setFlights)
    } else {
      void getFlightsLiveSnapshot().then((rows) => setFlights(rows.slice(0, 2)))
    }
    return () => stop()
  }, [enabled, timelineMode])

  useEffect(() => {
    if (!hostRef.current || viewerRef.current) return
    viewerRef.current = new Viewer(hostRef.current, {
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: true,
      infoBox: false,
      selectionIndicator: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
    })
    viewerRef.current.scene.globe.enableLighting = true

    return () => {
      viewerRef.current?.destroy()
      viewerRef.current = null
    }
  }, [])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer) return
    viewer.entities.removeAll()

    if (enabled['ports-reference']) {
      ports.forEach((port) => {
        viewer.entities.add({
          id: `port-${port.id}`,
          position: Cartesian3.fromDegrees(port.lon, port.lat),
          point: {
            pixelSize: 8,
            color: Color.CYAN.withAlpha(0.85),
            heightReference: HeightReference.CLAMP_TO_GROUND,
          },
          label: {
            text: port.name,
            fillColor: Color.WHITE,
            outlineColor: Color.BLACK,
            outlineWidth: 2,
            verticalOrigin: VerticalOrigin.TOP,
            pixelOffset: new Cartesian3(0, 20, 0),
            scale: 0.45,
          },
        })
      })
    }

    if (enabled['subsea-cables']) {
      cables.forEach((cable) => {
        const positions = cable.path.flatMap(([lat, lon]) => [lon, lat])
        viewer.entities.add({
          id: `cable-${cable.id}`,
          polyline: {
            positions: Cartesian3.fromDegreesArray(positions),
            width: cable.placeholder ? 2 : 3,
            material: cable.placeholder
              ? new PolylineDashMaterialProperty({
                  color: Color.ORANGE.withAlpha(0.85),
                })
              : Color.DEEPSKYBLUE.withAlpha(0.8),
          },
          description: cable.placeholder ? 'Placeholder route (no live cable data)' : cable.label,
        })
      })
    }

    if (enabled['flights-live']) {
      flights.forEach((flight) => {
        viewer.entities.add({
          id: `flight-${flight.id}`,
          position: Cartesian3.fromDegrees(flight.lon, flight.lat, flight.altitudeM),
          point: {
            pixelSize: 7,
            color: timelineMode === 'live' ? Color.LIME : Color.GOLD,
          },
          label: {
            text: `${flight.label} ${Math.round(flight.altitudeM / 100)}FL`,
            fillColor: Color.WHITE,
            verticalOrigin: VerticalOrigin.BOTTOM,
            scale: 0.45,
          },
        })
      })
    }

    if (timelineMode === 'replay') {
      viewer.clock.multiplier = 120
      viewer.clock.clockStep = ClockStep.SYSTEM_CLOCK_MULTIPLIER
      viewer.clock.clockRange = ClockRange.CLAMPED
    } else {
      viewer.clock.multiplier = 1
      viewer.clock.clockStep = ClockStep.SYSTEM_CLOCK
      viewer.clock.clockRange = ClockRange.UNBOUNDED
    }
    viewer.clock.shouldAnimate = true
  }, [cables, enabled, flights, ports, timelineMode])

  return (
    <section className="globe-workbench">
      <aside className="globe-workbench__catalogue">
        <h2>Data Layers</h2>
        <p className="globe-workbench__lead">
          Operational overlays with provenance and access controls.
        </p>
        <div className="globe-workbench__nav-tools" role="group" aria-label="Globe camera presets">
          {Object.entries(FOCUS_PRESETS).map(([key, preset]) => (
            <button
              key={key}
              type="button"
              className={activePreset === key ? 'is-selected' : undefined}
              onClick={() => moveCameraToPreset(key as FocusPresetId)}
            >
              {preset.label}
            </button>
          ))}
          <button type="button" onClick={focusOnVisibleEntities}>
            Fit Active Data
          </button>
        </div>
        <ul>
          {catalogue.map((layer) => (
            <li key={layer.id} className={selectedLayerId === layer.id ? 'is-active' : undefined}>
              <button
                type="button"
                onClick={() => setSelectedLayerId(layer.id)}
                className="globe-workbench__layer"
              >
                <input
                  type="checkbox"
                  checked={Boolean(enabled[layer.id])}
                  onChange={(event) =>
                    setEnabled((prev) => ({
                      ...prev,
                      [layer.id]: event.target.checked,
                    }))
                  }
                  aria-label={`toggle ${layer.name}`}
                />
                <span>{layer.name}</span>
                {layer.restricted ? <span className="badge badge--restricted">Restricted</span> : null}
                {layer.nonCommercial ? (
                  <span className="badge badge--non-commercial">Non-commercial</span>
                ) : null}
              </button>
              <p>{layer.description}</p>
            </li>
          ))}
        </ul>
      </aside>

      <div className="globe-workbench__globe">
        <div ref={hostRef} className="globe-workbench__viewer" />
      </div>

      <aside className="globe-workbench__inspector">
        <h2>Inspector</h2>
        <div className="globe-workbench__metrics">
          <div>
            <span className="globe-workbench__metric-label">Flights</span>
            <span className="globe-workbench__metric-value">{enabled['flights-live'] ? flights.length : 0}</span>
          </div>
          <div>
            <span className="globe-workbench__metric-label">Ports</span>
            <span className="globe-workbench__metric-value">{enabled['ports-reference'] ? ports.length : 0}</span>
          </div>
          <div>
            <span className="globe-workbench__metric-label">Cables</span>
            <span className="globe-workbench__metric-value">{enabled['subsea-cables'] ? cables.length : 0}</span>
          </div>
        </div>
        {selectedLayer ? (
          <dl>
            <dt>Layer</dt>
            <dd>{selectedLayer.name}</dd>
            <dt>Provenance</dt>
            <dd>{selectedLayer.metadata.provenance}</dd>
            <dt>Confidence</dt>
            <dd>{Math.round(selectedLayer.metadata.confidence * 100)}%</dd>
            <dt>Source</dt>
            <dd>{selectedLayer.metadata.source}</dd>
            <dt>Access</dt>
            <dd>{selectedLayer.metadata.access}</dd>
            <dt>Licence</dt>
            <dd>{selectedLayer.metadata.licence}</dd>
          </dl>
        ) : (
          <p>Select a layer to inspect provenance and controls.</p>
        )}
      </aside>

      <footer className="globe-workbench__timeline">
        <div>
          <h3>Timeline Mode</h3>
          <p>
            {timelineMode === 'live'
              ? 'Live stream: current flight positions with periodic refresh.'
              : 'Replay mode: accelerated timeline for demonstration and review.'}
          </p>
        </div>
        <div className="globe-workbench__timeline-controls">
          <button
            type="button"
            className={timelineMode === 'live' ? 'is-selected' : undefined}
            onClick={() => setTimelineMode('live')}
          >
            Live
          </button>
          <button
            type="button"
            className={timelineMode === 'replay' ? 'is-selected' : undefined}
            onClick={() => setTimelineMode('replay')}
          >
            Replay
          </button>
        </div>
      </footer>
    </section>
  )
}
