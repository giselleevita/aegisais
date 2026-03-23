/**
 * Globe camera observability: dispatches DOM events and optional dev logging.
 * Hook PostHog or other analytics by listening on `window` for `aegis-globe-camera`.
 */

export type GlobeCameraMoveReason = 'preset' | 'fit-visible' | 'auto-initial'

export type GlobeCameraTelemetryDetail =
  | {
      type: 'camera_move_applied'
      reason: GlobeCameraMoveReason
    }
  | {
      type: 'camera_move_blocked'
      reason: 'user_lock' | 'auto_disabled'
      attempted: GlobeCameraMoveReason
    }
  | {
      type: 'auto_camera_changed'
      enabled: boolean
    }

const EVENT_NAME = 'aegis-globe-camera'

export function emitGlobeCameraTelemetry(detail: GlobeCameraTelemetryDetail): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail }))
  if (import.meta.env.DEV) {
    console.debug('[globe-camera]', detail)
  }
}

/** Subscribe from tests, devtools, or future analytics wiring. */
export function subscribeGlobeCameraTelemetry(
  handler: (detail: GlobeCameraTelemetryDetail) => void
): () => void {
  if (typeof window === 'undefined') return () => {}
  const listener = (ev: Event) => {
    const ce = ev as CustomEvent<GlobeCameraTelemetryDetail>
    if (ce.detail) handler(ce.detail)
  }
  window.addEventListener(EVENT_NAME, listener)
  return () => window.removeEventListener(EVENT_NAME, listener)
}
