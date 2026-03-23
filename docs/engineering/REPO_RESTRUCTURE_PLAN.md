# Repo Restructure Plan

## Objective

Evolve AegisAIS into a modular geospatial intelligence platform without a blind rewrite, preserving existing maritime workflows while adding a 3D layer-driven analyst workbench.

## Principles

- Incremental, backward-compatible integration.
- Contract-first APIs and schemas.
- Server-side licensing and secret handling only.
- Provenance/confidence/access metadata mandatory for every layer and object.

## Phases

### Phase 1: Contracts and Architecture Baseline

- Establish canonical schemas in `packages/contracts/schemas`.
- Define BFF OpenAPI and route contracts for layers/query/search/entities/tracks/events/stream.
- Add docs and layer catalog governance.

### Phase 2: Vertical Slice Enablement

- Deploy BFF with auth stub, rate limiting, caching, WS stream.
- Add OpenSky adapter (quota + cache + canonical mapping).
- Add World Port Index + UN/LOCODE importer.
- Add minimal PostGIS schema for layer assets and geospatial joins.

### Phase 3: Analyst Workbench UI

- Add Cesium globe route in AML shell.
- Layer catalogue from BFF `/v1/layers`.
- Inspector with provenance/confidence/access/licence.
- Timeline with Live/Replay toggle.

### Phase 4: Detection and Incidents

- Add explainable cable-proximity fused rule.
- Create incident from alert with evidence bundle and schema versions.
- Add metrics/tracing hooks and deterministic replay tests.

### Phase 5: Hardening and Consolidation

- Strengthen tenancy boundaries, audit export/edit actions.
- Expand license gates per provider.
- Decommission redundant pathways once parity and tests are complete.

## Risk Controls

- No claimed live subsurface tracking; only inferred zones, stubs, and simulation.
- Restricted/non-commercial layers default off unless licensed.
- Secrets remain server-side (BFF/API env only).
- Build/test gates on every increment (API tests, web build/e2e, BFF build).
