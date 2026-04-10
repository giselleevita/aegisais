import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react'
import type { LayerDefinition } from '@/shared/types/common'
import type { CableSegment, FlightPoint, PortPoint } from '@/features/globe/globeData'
import type { GlobeCameraTelemetryDetail } from '@/features/globe/globeCameraTelemetry'
import { FOCUS_PRESETS, type CameraCommand, type FocusPresetId, type TimelineMode } from '@/features/globe/globeWorkbenchConfig'
import './globe-workbench.css'

const AUTO_CAMERA_STORAGE_KEY = 'aegis.globe.autoCamera'

let globeDataModulePromise: Promise<typeof import('@/features/globe/globeData')> | null = null
let globeTelemetryModulePromise: Promise<typeof import('@/features/globe/globeCameraTelemetry')> | null = null
const GlobeViewerRuntime = lazy(() => import('@/aml/pages/GlobeViewerRuntime'))

function loadGlobeDataModule() {
  globeDataModulePromise ??= import('@/features/globe/globeData')
  return globeDataModulePromise
}

function loadGlobeTelemetryModule() {
  globeTelemetryModulePromise ??= import('@/features/globe/globeCameraTelemetry')
  return globeTelemetryModulePromise
}

function emitGlobeCameraTelemetry(detail: GlobeCameraTelemetryDetail) {
  void loadGlobeTelemetryModule().then((module) => {
    module.emitGlobeCameraTelemetry(detail)
  })
}

function GlobeViewerFallback() {
  return (
    <div className="globe-workbench__viewer globe-workbench__viewer--loading">
      <div className="globe-workbench__viewer-placeholder">
        <strong>Loading 3D globe</strong>
        <span>Cesium runtime is fetched only when this workspace is opened.</span>
      </div>
    </div>
  )
}

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

export default function GlobeWorkbenchPage() {
  const [timelineMode, setTimelineMode] = useState<TimelineMode>('live')
  const [autoCameraEnabled, setAutoCameraEnabled] = useState(() => readAutoCameraPref())
  const [catalogue, setCatalogue] = useState<LayerDefinition[]>([])
  const [enabled, setEnabled] = useState<Record<string, boolean>>({})
  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(null)
  const [activePreset, setActivePreset] = useState<FocusPresetId>('global')
  const [flights, setFlights] = useState<FlightPoint[]>([])
  const [ports, setPorts] = useState<PortPoint[]>([])
  const [cables, setCables] = useState<CableSegment[]>([])
  const [cameraCommand, setCameraCommand] = useState<CameraCommand | null>(null)
  const visibleFlights = enabled['flights-live'] ? flights : []

  const selectedLayer = useMemo(
    () => catalogue.find((layer) => layer.id === selectedLayerId) ?? null,
    [catalogue, selectedLayerId]
  )

  const setAutoCameraEnabledPersisted = useCallback((next: boolean) => {
    setAutoCameraEnabled(next)
    try {
      localStorage.setItem(AUTO_CAMERA_STORAGE_KEY, String(next))
    } catch {
      /* ignore */
    }
    emitGlobeCameraTelemetry({ type: 'auto_camera_changed', enabled: next })
  }, [])

  const queueCameraCommand = useCallback((next: { type: 'preset'; presetId: FocusPresetId } | { type: 'fit-visible' }) => {
    setCameraCommand((previous) => {
      const sequence = (previous?.sequence ?? 0) + 1
      if (next.type === 'preset') {
        return { type: 'preset', presetId: next.presetId, sequence }
      }
      return { type: 'fit-visible', sequence }
    })
  }, [])

  useEffect(() => {
    let cancelled = false
    void loadGlobeDataModule().then(async (module) => {
      const [rows, portRows, cableRows] = await Promise.all([
        module.getLayerCatalogue(),
        module.getPortsReference(),
        module.getSubseaCables(),
      ])
      if (cancelled) return
      setCatalogue(rows)
      setSelectedLayerId(rows[0]?.id ?? null)
      const nextEnabled: Record<string, boolean> = {}
      rows.forEach((layer) => {
        nextEnabled[layer.id] = layer.enabledByDefault ?? true
      })
      setEnabled(nextEnabled)
      setPorts(portRows)
      setCables(cableRows)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const moveCameraToPreset = useCallback((presetId: FocusPresetId) => {
    setActivePreset(presetId)
    queueCameraCommand({ type: 'preset', presetId })
  }, [queueCameraCommand])

  const focusOnVisibleEntities = useCallback(() => {
    setActivePreset('global')
    queueCameraCommand({ type: 'fit-visible' })
  }, [queueCameraCommand])

  useEffect(() => {
    let stop: () => void = () => {}
    if (!enabled['flights-live']) return
    let cancelled = false
    void loadGlobeDataModule().then((module) => {
      if (cancelled) return
      if (timelineMode === 'live') {
        void module.getFlightsLiveSnapshot().then(setFlights)
        stop = module.subscribeFlightsLive((next) => {
          if (!cancelled) setFlights(next)
        })
      } else {
        void module.getFlightsLiveSnapshot().then((rows) => setFlights(rows.slice(0, 2)))
      }
    })
    return () => {
      cancelled = true
      stop()
    }
  }, [enabled, timelineMode])

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
        <Suspense fallback={<GlobeViewerFallback />}>
          <GlobeViewerRuntime
            enabled={enabled}
            ports={ports}
            cables={cables}
            flights={visibleFlights}
            timelineMode={timelineMode}
            autoCameraEnabled={autoCameraEnabled}
            cameraCommand={cameraCommand}
            onTelemetry={emitGlobeCameraTelemetry}
          />
        </Suspense>
      </div>

      <aside className="globe-workbench__inspector">
        <h2>Inspector</h2>
        <div className="globe-workbench__metrics">
          <div>
            <span className="globe-workbench__metric-label">Flights</span>
            <span className="globe-workbench__metric-value">{visibleFlights.length}</span>
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
