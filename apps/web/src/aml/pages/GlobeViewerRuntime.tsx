import { useCallback, useEffect, useRef } from 'react'
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
import type { CableSegment, FlightPoint, PortPoint } from '@/features/globe/globeData'
import type { GlobeCameraTelemetryDetail } from '@/features/globe/globeCameraTelemetry'
import { FOCUS_PRESETS, type CameraCommand, type TimelineMode } from '@/features/globe/globeWorkbenchConfig'

const USER_CAMERA_PRIORITY_WINDOW_MS = 5000
const MIN_CAMERA_DISTANCE_METERS = 850_000
const MAX_CAMERA_DISTANCE_METERS = 32_000_000

type GlobeViewerRuntimeProps = {
  enabled: Record<string, boolean>
  ports: PortPoint[]
  cables: CableSegment[]
  flights: FlightPoint[]
  timelineMode: TimelineMode
  autoCameraEnabled: boolean
  cameraCommand: CameraCommand | null
  onTelemetry: (detail: GlobeCameraTelemetryDetail) => void
}

export default function GlobeViewerRuntime({
  enabled,
  ports,
  cables,
  flights,
  timelineMode,
  autoCameraEnabled,
  cameraCommand,
  onTelemetry,
}: GlobeViewerRuntimeProps) {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const viewerRef = useRef<Viewer | null>(null)
  const userCameraLockRef = useRef(false)
  const userCameraLockTimerRef = useRef<number | null>(null)
  const autoFramedOnceRef = useRef(false)
  const autoCameraEnabledRef = useRef(autoCameraEnabled)
  const latestCameraCommandRef = useRef<CameraCommand | null>(cameraCommand)

  useEffect(() => {
    latestCameraCommandRef.current = cameraCommand
  }, [cameraCommand])

  useEffect(() => {
    autoCameraEnabledRef.current = autoCameraEnabled
  }, [autoCameraEnabled])

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
    (reason: 'preset' | 'fit-visible' | 'auto-initial', runMove: (viewer: Viewer) => void) => {
      const viewer = viewerRef.current
      if (!viewer) return false
      const passive = reason === 'auto-initial'
      if (passive && !autoCameraEnabledRef.current) {
        onTelemetry({
          type: 'camera_move_blocked',
          reason: 'auto_disabled',
          attempted: reason,
        })
        return false
      }
      if (passive && userCameraLockRef.current) {
        onTelemetry({
          type: 'camera_move_blocked',
          reason: 'user_lock',
          attempted: reason,
        })
        return false
      }
      runMove(viewer)
      onTelemetry({ type: 'camera_move_applied', reason })
      return true
    },
    [onTelemetry]
  )

  const runCameraCommand = useCallback(
    (command: CameraCommand) => {
      if (command.type === 'preset') {
        const preset = FOCUS_PRESETS[command.presetId]
        void moveCamera('preset', (viewer) => {
          viewer.camera.flyTo({
            destination: Cartesian3.fromDegrees(preset.lon, preset.lat, preset.height),
            duration: 1.1,
            orientation: {
              heading: 0,
              pitch: -0.95,
              roll: 0,
            },
          })
        })
        return
      }
      void moveCamera('fit-visible', (viewer) => {
        void viewer.flyTo(viewer.entities.values, {
          duration: 1.15,
          maximumHeight: MAX_CAMERA_DISTANCE_METERS,
          offset: new HeadingPitchRange(0, -0.95, 4_000_000),
        })
      })
    },
    [moveCamera]
  )

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

    if (latestCameraCommandRef.current) {
      runCameraCommand(latestCameraCommandRef.current)
    }

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
  }, [markUserInteraction, runCameraCommand])

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
    if (viewer.entities.values.length === 0) return
    const moved = moveCamera('auto-initial', (activeViewer) => {
      void activeViewer.flyTo(activeViewer.entities.values, {
        duration: 1.2,
        maximumHeight: MAX_CAMERA_DISTANCE_METERS,
        offset: new HeadingPitchRange(0, -0.95, 6_000_000),
      })
    })
    if (moved) autoFramedOnceRef.current = true
  }, [autoCameraEnabled, cables, enabled, flights, moveCamera, ports])

  useEffect(() => {
    if (!cameraCommand || !viewerRef.current) return
    runCameraCommand(cameraCommand)
  }, [cameraCommand, runCameraCommand])

  return <div ref={hostRef} className="globe-workbench__viewer" />
}