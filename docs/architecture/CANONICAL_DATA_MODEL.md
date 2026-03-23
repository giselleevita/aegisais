# Canonical Geospatial Data Model

This document defines the canonical object model used by the target geospatial architecture and reflected by contract schemas in `packages/contracts/schemas`.

## Cross-Cutting Metadata

Every externally visible object includes:

- `confidence`: quality estimate and derivation method.
- `provenance`: source and transformation lineage.
- `access`: classification and authorization hints.

## Core Objects

### LayerDefinition

Describes discoverable layers exposed by `/v1/layers`.

Key fields:

- identity: `id`, `name`, `description`
- behavior: `geometryType`, `entityType`, `queryable`, `streamable`
- policy: `access`
- trust: `confidence`, `provenance`

### Entity

Represents a tracked object (vessel, facility, sensor, etc.) with latest state.

Key fields:

- identity: `id`, `entityType`, optional aliases
- state: `position`, `heading`, `speed`, `status`
- timestamps: `observedAt`, `updatedAt`
- metadata: `confidence`, `provenance`, `access`

### Observation

Atomic measurement point from a source feed or derived process.

Key fields:

- identity: `id`, `entityId`, `layerId`
- measurement: `geometry`, `properties`
- time: `observedAt`, optional `ingestedAt`
- metadata: `confidence`, `provenance`, `access`

### Track

Temporal/spatial sequence for an entity over a time window.

Key fields:

- identity: `id`, `entityId`, `layerId`
- extents: `startTime`, `endTime`, optional bbox
- data: ordered `points` (observations or simplified points)
- metadata: `confidence`, `provenance`, `access`

### Event

Time-bounded occurrence derived from observations/rules.

Key fields:

- identity: `id`, `eventType`, optional `incidentId`
- participants: `entityIds`
- geometry/time: `geometry`, `occurredAt`, optional `endedAt`
- severity/context: `severity`, `attributes`
- metadata: `confidence`, `provenance`, `access`

### Alert

Analyst-facing actionable signal derived from events/rules.

Key fields:

- identity: `id`, `alertType`, optional `eventId`
- lifecycle: `status`, `createdAt`, optional `acknowledgedAt`, `resolvedAt`
- triage: `priority`, `message`, optional `assignee`
- metadata: `confidence`, `provenance`, `access`

### Incident

Aggregate investigative case grouping events/alerts/entities.

Key fields:

- identity: `id`, `title`, `status`
- graph: `entityIds`, `eventIds`, `alertIds`
- lifecycle: `createdAt`, `updatedAt`, optional closure fields
- metadata: `confidence`, `provenance`, `access`

## Reference Metadata Objects

### Confidence

- `score`: normalized [0..1]
- `method`: rule/model/source method id
- optional `lowerBound`, `upperBound`, `notes`

### Provenance

- `source`: upstream data system
- `sourceRecordId`: original id
- `processor`: service or pipeline stage
- `ingestedAt`: timestamp
- optional `lineage`: ordered transformation steps

## Access Model

`access` metadata is carried on both layer definitions and data objects:

- `classification`: e.g. `public`, `internal`, `restricted`, `secret`
- `allowedRoles`: coarse role list for clients/bff checks
- optional `compartments`: fine-grained tags
- optional `ownerOrgId`: tenancy and organization scoping

## Relationships

- `LayerDefinition` 1..* `Observation`
- `Entity` 1..* `Observation`
- `Entity` 1..* `Track`
- `Event` *..* `Entity`
- `Alert` 0..1 `Event`
- `Incident` * `Event`, * `Alert`, * `Entity`

## Contract Notes

- Object ids are opaque strings.
- Timestamps use RFC 3339 date-time.
- Unknown properties are disallowed unless schema explicitly allows an extension map.
