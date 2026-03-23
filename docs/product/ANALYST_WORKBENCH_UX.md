# Analyst Workbench UX

## Goal

Provide an analyst-focused 3D globe workspace that complements existing maritime AML workflows without replacing or regressing the current operations/map pages.

## Route and placement

- New route: `/globe` in AML navigation.
- Existing `/triage`, `/map`, `/lab`, `/itdae`, `/watchlist`, `/admin`, `/about` remain unchanged.
- Legacy UI toggle and legacy route behavior remain unchanged.

## Layout

Three-pane desktop workbench with persistent timeline rail:

- Left: Layer Catalogue (source of truth from `GET /v1/layers`, with fallback stubs).
- Center: Cesium globe canvas with overlays.
- Right: Inspector drawer for selected layer metadata.
- Bottom: Timeline strip with `Live` and `Replay` mode toggle.

## Layer catalogue behavior

- Each layer has:
  - enable/disable checkbox
  - title + short description
  - optional badges:
    - `Restricted`
    - `Non-commercial`
- Catalogue defaults:
  - Flights Live: enabled
  - Ports: enabled
  - Subsea Cables: disabled

When `GET /v1/layers` is unavailable, the UI falls back to local stub definitions so the route remains operable in local/dev mode.

## Inspector drawer behavior

Clicking a layer in the catalogue populates inspector fields:

- provenance
- confidence
- source
- access
- licence

If no layer is selected, inspector shows prompt text.

## Timeline behavior

- `Live`:
  - uses flight snapshot + stream stub updates
  - renders moving flight points
- `Replay`:
  - uses snapshot subset
  - globe clock runs with higher multiplier for simulated playback

This timeline is scoped to workbench overlays and does not alter existing replay controls in `/lab`.

## Initial overlay set

- Flights Live:
  - query stub: `GET /v1/bff/flights/live`
  - stream stub: interval updates in UI service until backend stream is available
- Ports:
  - reference point dataset (static starter list)
- Subsea Cables:
  - tries `GET /v1/bff/subsea-cables`
  - falls back to dashed placeholder polyline when no data

## Access and licensing cues

Restricted/non-commercial labels are visible in the catalogue to prevent accidental misuse of gated layers.

## Non-goals in this slice

- No replacement of existing maritime map workflows.
- No backend schema changes in this frontend increment.
- No analyst permissions enforcement logic in UI; server remains source of truth.
