import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Cartesian3,
  ClockRange,
  ClockStep,
  Color,
  HeadingPitchRange,
  HeightReference,
  PolylineDashMaterialProperty,
  ScreenSpaceEventType,
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
import { emitGlobeCameraTelemetry } from '@/features/globe/globeCameraTelemetry'
import './globe-workbench.css'

type TimelineMode = 'live' | 'replay'
type FocusPresetId = 'global' | 'atlantic' | 'indo-pacific' | 'europe-med'
type CameraMoveReason = 'preset' | 'fit-visible' | 'auto-initial'

const AUTO_CAMERA_STORAGE_KEY = 'aegis.globe.autoCamera'

const USER_CAMERA_PRIORITY_WINDOW_MS = 5000
const MIN_CAMERA_DISTANCE_METERS = 850_000
const MAX_CAMERA_DISTANCE_METERS = 32_000_000

function readAutoCameraPref(): boolean {
  try {
    const v = localStorage.getItem(AUTO_CAMERA_STORAGE_KEY)
    if (v === 'false') return false
    if (v === 'true') return true
  } catch {
    /* ignore */
  }
  return true
}

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
  const userCameraLockRef = useRef(false)
  const userCameraLockTimerRef = useRef<number | null>(null)
  const autoFramedOnceRef = useRef(false)

  const [timelineMode, setTimelineMode] = useState<TimelineMode>('live')
  const [autoCameraEnabled, setAutoCameraEnabled] = useState(() => readAutoCameraPref())
  const autoCameraEnabledRef = useRef(autoCameraEnabled)
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
    autoCameraEnabledRef.current = autoCameraEnabled
  }, [autoCameraEnabled])

  const setAutoCameraEnabledPersisted = useCallback((next: boolean) => {
    setAutoCameraEnabled(next)
    try {
      localStorage.setItem(AUTO_CAMERA_STORAGE_KEY, String(next))
    } catch {
      /* ignore */
    }
    emitGlobeCameraTelemetry({ type: 'auto_camera_changed', enabled: next })
  }, [])

  const markUserInteraction = useCallback(() => {
    userCameraLockRef.current = true
    if (userCameraLockTimerRef.current !== null) {
      window.clearTimeout(userCameraLockTimerRef.current)
    }
    userCameraLockTimerRef.current = window.setTimeout(() => {
      userCameraLockRef.current = false
      userCameraLockTimerRef.current = null
    }, USER_CAMERA_PRIORITY_WINDOW_MS)
  }, [])

  const moveCamera = useCallback(
    (reason: CameraMoveReason, runMove: (viewer: Viewer) => void, options?: { force?: boolean }) => {
      const viewer = viewerRef.current
      if (!viewer) return false
      const passive = reason === 'auto-initial'
      if (passive && !options?.force && !autoCameraEnabledRef.current) {
        emitGlobeCameraTelemetry({
          type: 'camera_move_blocked',
          reason: 'auto_disabled',
          attempted: reason,
        })
        return false
      }
      if (passive && !options?.force && userCameraLockRef.current) {
        emitGlobeCameraTelemetry({
          type: 'camera_move_blocked',
          reason: 'user_lock',
          attempted: reason,
        })
        return false
      }
      runMove(viewer)
      emitGlobeCameraTelemetry({ type: 'camera_move_applied', reason })
      return true
    },
    []
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

  const moveCameraToPreset = useCallback((presetId: FocusPresetId) => {
    setActivePreset(presetId)
    const preset = FOCUS_PRESETS[presetId]
    void moveCamera('preset', (viewer) => {
      viewer.camera.flyTo({
        destination: preset.destination,
        duration: 1.1,
        orientation: {
          heading: 0,
          pitch: -0.95,
          roll: 0,
        },
      })
    })
  }, [moveCamera])

  const focusOnVisibleEntities = useCallback(() => {
    setActivePreset('global')
    void moveCamera('fit-visible', (viewer) => {
      void viewer.flyTo(viewer.entities.values, {
        duration: 1.15,
        maximumHeight: MAX_CAMERA_DISTANCE_METERS,
        offset: new HeadingPitchRange(0, -0.95, 4_000_000),
      })
    })
  }, [moveCamera])

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
    const viewer = viewerRef.current
    viewer.scene.globe.enableLighting = true
    viewer.trackedEntity = undefined

    const cameraController = viewer.scene.screenSpaceCameraController
    cameraController.inertiaZoom = 0.45
    cameraController.minimumZoomDistance = MIN_CAMERA_DISTANCE_METERS
    cameraController.maximumZoomDistance = MAX_CAMERA_DISTANCE_METERS

    // Reduce accidental zoom jumps from double-click interactions.
    viewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(ScreenSpaceEventType.LEFT_DOUBLE_CLICK)

    const canvas = viewer.scene.canvas
    const onWheel = () => markUserInteraction()
    const onPointerDown = () => markUserInteraction()
    const onTouchStart = () => markUserInteraction()
    const onKeyDown = (event: KeyboardEvent) => {
      if (['+', '=', '-', '_', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
        markUserInteraction()
      }
    }

    canvas.addEventListener('wheel', onWheel, { passive: true })
    canvas.addEventListener('pointerdown', onPointerDown)
    canvas.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('keydown', onKeyDown)

    return () => {
      canvas.removeEventListener('wheel', onWheel)
      canvas.removeEventListener('pointerdown', onPointerDown)
      canvas.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('keydown', onKeyDown)
      if (userCameraLockTimerRef.current !== null) {
        window.clearTimeout(userCameraLockTimerRef.current)
        userCameraLockTimerRef.current = null
      }
      viewerRef.current?.destroy()
      viewerRef.current = null
    }
  }, [markUserInteraction])

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

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || autoFramedOnceRef.current) return
    if (!autoCameraEnabled) return
    if (viewer.entities.values.length === 0) return
    const moved = moveCamera(
      'auto-initial',
      (activeViewer) => {
        void activeViewer.flyTo(activeViewer.entities.values, {
          duration: 1.2,
          maximumHeight: MAX_CAMERA_DISTANCE_METERS,
          offset: new HeadingPitchRange(0, -0.95, 6_000_000),
        })
      },
      { force: false }
    )
    if (moved) autoFramedOnceRef.current = true
  }, [autoCameraEnabled, cables, enabled, flights, moveCamera, ports])

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
        <div className="globe-workbench__auto-camera">
          <div className="globe-workbench__auto-camera-row">
            <label className="globe-workbench__auto-camera-label" htmlFor="globe-auto-camera">
              Auto camera
            </label>
            <input
              id="globe-auto-camera"
              type="checkbox"
              role="switch"
              className="globe-workbench__auto-camera-switch"
              checked={autoCameraEnabled}
              onChange={(e) => setAutoCameraEnabledPersisted(e.target.checked)}
              aria-describedby="globe-auto-camera-help"
            />
          </div>
          <p id="globe-auto-camera-help" className="globe-workbench__auto-camera-help">
            Off: no automatic framing when layers load; use presets or Fit Active Data.
          </p>
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
