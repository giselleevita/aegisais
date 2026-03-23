# Target Modular Geospatial Architecture

## Goals

- Keep a modular-monolith runtime while enforcing contract-first boundaries.
- Separate geospatial read/query concerns from ingestion and rule evaluation.
- Make confidence, provenance, and access metadata first-class on layers and domain objects.
- Enable web and API clients to consume stable, versioned contracts.

## Target Modules

### 1) Ingest and Normalization

- Sources AIS/events/external feed data into canonical `Observation` records.
- Performs schema validation and provenance stamping at ingest time.
- Emits normalized records to storage and stream bus.

### 2) Entity and Track Store

- Maintains current `Entity` state and historical `Track` segments.
- Supports temporal and spatial indexing for search and query APIs.
- Enforces object-level access metadata for retrieval.

### 3) Event and Alert Engine

- Converts observations and rules into `Event` and `Alert` outputs.
- Produces `Incident` aggregates for analyst workflows.
- Carries confidence and provenance through derivation chain.

### 4) Layer Catalog and Query API (BFF)

- Serves client-facing routes under `/v1/*` from a contract-first OpenAPI spec.
- Returns layer catalog, search results, entity details, tracks, and event feeds.
- Exposes bounded query interface and websocket stream contract.

### 5) Policy and Access Module

- Resolves caller context into dataset/layer/object permissions.
- Applies access constraints at layer, object, and field levels.
- Provides consistent denial/redaction behavior to all API handlers.

## Runtime Architecture

1. **Ingest path**: source -> normalization -> observation store -> event/alert generation.
2. **Read path**: client -> BFF contract routes -> policy checks -> geo/entity/event stores.
3. **Realtime path**: observation/event updates -> stream broker -> `/v1/stream` websocket consumers.

## Contract Boundaries

- `packages/contracts/schemas/*` is the source of truth for canonical payloads.
- `apps/bff/openapi.yaml` references contract payload semantics and route behavior.
- Internal modules may evolve implementation details but must preserve contract compatibility.

## Data and Storage Strategy

- **Primary OLTP**: PostgreSQL + PostGIS for entities, tracks, and events.
- **Hot cache (optional)**: Redis for short-lived query acceleration and stream fanout.
- **Object payload storage (optional)**: blob store for large raw artifacts linked in provenance.

## Metadata Requirements

All layer definitions and data objects carry:

- `confidence`: score, method, and optional bounds.
- `provenance`: source, processor chain, and timestamps.
- `access`: classification, allowed roles, and optional compartment tags.

These fields are required for authorization and analyst trust workflows.

## Deployment Shape

- `apps/api`: domain/infrastructure services (ingest, detection, auth, admin).
- `apps/bff`: contract-first geospatial experience API for web and external consumers.
- Shared `packages/contracts`: JSON Schemas and generated TypeScript types.

## Evolution Rules

- Additive schema changes only on `v1`.
- Breaking changes require new API version namespace.
- New modules must publish contract changes before implementation rollout.
