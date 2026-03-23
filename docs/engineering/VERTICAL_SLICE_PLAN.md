# Vertical Slice Plan

## Working

- **Repo and architecture foundation**
  - Repo audit and restructure plan are documented.
  - Target architecture, canonical data model, BFF OpenAPI, and JSON schemas are in place.
- **Contracts**
  - Canonical schemas created for LayerDefinition, Entity, Observation, Track, Event, Alert, Incident, Provenance, Confidence.
- **BFF slice (`apps/bff`)**
  - Auth middleware stub, layer manifest, cache/rate limiting, websocket stream endpoint.
  - License-aware layer gating in manifest.
- **Data adapters/importers**
  - OpenSky adapter with quota controls, caching, and canonical mapping.
  - World Port Index + UN/LOCODE importer for PostGIS-friendly reference storage.
- **Frontend 3D workbench**
  - Cesium-based AML globe page with layer catalogue, inspector drawer, and timeline live/replay toggle.
  - Restricted/non-commercial badges rendered for gated layers.
- **Detection + incidents**
  - Explainable fused rule: surface activity near cable segment within time window => alert.
  - Alert-to-incident creation with evidence bundle containing provenance/schema version fields.
- **Validation**
  - Backend tests passing.
  - Web build and e2e passing.
  - BFF build/lint passing.
  - Docker compose config validates with db+bff+web entries.

## Stubbed

- Partner-only feeds (FAA SWIM, EUROCONTROL NM B2B, Digital NOTAM, SAR/RF partner connectors) are interfaces/docs only.
- TeleGeography live ingestion is import-contract based; no licensed dataset bundled.
- Global Fishing Watch integration is documented and gated as non-commercial by policy.
- Incident UI workflows (assignment/escalation/SLA lifecycle) are partial.
- Centralized policy engine for legal/licensing attestation is not fully implemented.

## Blocked

- Live partner feeds requiring credentials/contracts are blocked by missing licenses/keys.
- Production legal approval for any subsurface-related operational claims remains pending.
- Full rollout of PostGIS canonical storage depends on deployment/migration scheduling in target environments.
