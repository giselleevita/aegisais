# Architecture

## High-Level Description

AegisAIS is organized as a web application with a FastAPI backend and a React frontend. The backend is described as a modular monolith: domain logic is separated into modules, but deployment remains simple and centralized.

At a high level, the system:

- ingests AIS data files
- replays or streams those records through detection logic
- stores alert and vessel state in a database
- exposes operational workflows through API endpoints and a browser UI

## Modular Monolith Model

The modular monolith pattern is explicitly described in the source material. The design separates concerns by feature and technical function while avoiding distributed-service complexity.

Core properties of the current approach:

- a single backend application boundary
- domain-specific modules for alerts, vessels, and ITDAE logic
- shared infrastructure for replay, ingest, logging, database access, and websocket delivery
- a feature-based frontend organized around alerts, vessels, map, and ITDAE workflows

## Component Breakdown

## Frontend

Primary responsibilities:

- vessel and alert visualization
- analyst investigation workflows
- status updates and notes
- filtering, export, and onboarding

Documented frontend capabilities include:

- alerts panel
- vessel details view
- map visualization
- onboarding and demo mode
- realtime updates through websocket-based hooks

## API Layer

Primary responsibilities:

- health and metrics endpoints
- upload and replay control
- vessel and track retrieval
- alert retrieval, export, and status management
- OpenAPI/Swagger documentation

Representative endpoint groups referenced in the documentation:

- `/v1/health`
- `/v1/metrics`
- `/v1/vessels`
- `/v1/vessels/{mmsi}/track`
- `/v1/alerts`
- `/v1/alerts/export/*`
- `/v1/upload`
- `/v1/replay/start`
- websocket stream endpoints

## Domain Logic

The backend is grouped around domain-specific and infrastructure concerns.

Domain-oriented areas documented in the codebase structure:

- `alerts`
- `vessels`
- `itdae`
- legacy `detection`, `tracking`, and `services` areas

Infrastructure-oriented areas documented in the codebase structure:

- ingest loaders and replay
- websocket management
- database configuration
- logging
- middleware

## Database Layer

The documentation describes a mixed deployment model:

- SQLite for smaller or simpler setups
- PostgreSQL recommended for large datasets and production-style workloads

Documented database responsibilities include:

- storing alerts and alert metadata
- storing vessel latest-state data
- storing historical vessel positions
- storing alert cooldown state

## Domain Model Summary

## Alerts Domain

Documented entities and fields:

- `alerts`
- alert status values: `new`, `reviewed`, `resolved`, `false_positive`
- alert notes/comments
- alert severity
- alert evidence payload
- alert cooldown tracking

## Vessels and Tracking Domain

Documented entities and fields:

- `vessels_latest`
- `vessel_positions`
- historical track storage by MMSI and timestamp
- current vessel position and track retrieval

## ITDAE Domain

The source materials identify an `itdae` module and feature area, but do not provide a detailed domain narrative beyond its presence as a specialized module.

## Data and Replay Domain

Documented responsibilities:

- upload and replay AIS files
- streaming for large datasets
- replay speed control
- batch processing

## Request Flow Diagrams

## AIS File Processing Flow

```text
User/API Client
    |
    v
Upload or Replay Request
    |
    v
API Layer
    |
    v
Replay / Streaming Engine
    |
    v
Detection Rules + Pipeline
    |
    +--> Alert Records
    |
    +--> Vessel State Updates
    |
    v
Database
```

## Analyst Review Flow

```text
Analyst
    |
    v
Frontend UI
    |
    v
API Query
    |
    +--> Alerts
    +--> Vessel Details
    +--> Track History
    |
    v
Database
    |
    v
Frontend Review / Status Update / Export
```

## Auth Model

The repository contains an authentication layer with:

- `/v1/auth/login` and `/v1/auth/register`
- JWT token creation and decoding
- OAuth2 password-bearer dependency wiring
- route-level `get_current_user` and `require_admin` enforcement on multiple API routes

However, the production-hardening model is still incomplete in the documented operating posture:

- broader infrastructure hardening remains outside the base system scope
- deployment guidance still assumes additional authentication, authorization, and network controls around the platform
- configuration currently includes a default local secret key value intended to be changed in production

Current architectural implication:

- authentication is present in code
- production trust still depends on secret management, route coverage review, and surrounding deployment controls

## Data Flow

The documented data flow is:

1. AIS files are uploaded or referenced for replay.
2. Replay or streaming logic reads and batches AIS points.
3. Detection rules evaluate consistency and suspicious behavior.
4. Alerts and vessel state are persisted.
5. Analysts retrieve alerts, tracks, and vessel views through the API and UI.
6. Filtered alert sets can be exported.

## External Integrations

Documented and implied integrations in the source materials include:

- AIS data files as the primary source input
- PostgreSQL for larger or production-style deployments
- SQLite for local or smaller-scale operation
- websocket delivery for realtime UI updates
- OpenAPI and Swagger documentation interfaces
- Docker-based deployment

Items explicitly identified as not yet implemented:

- realtime AIS feed ingestion
- webhook integrations
- notification integrations
- external vessel metadata services

## Deployment Inference

This section combines documented deployment guidance with repository configuration.

Repository configuration currently indicates:

- a browser-based frontend
- a backend API service
- PostgreSQL and Redis services in Docker
- additional ingestion and worker-style services in the Docker compose setup
- SQLite as a local default and PostgreSQL as the recommended larger-scale database

The exact production topology is still not documented as a finalized target architecture, so the deployment model should be treated as partially inferred rather than fully specified.

## Architectural Constraints

- The system is designed as a modular monolith, not a distributed service mesh.
- The documented primary ingestion mode is file-based rather than live feed processing.
- The tool is scoped as a research and analyst support component, not a full maritime security platform.
- Production controls such as authN/Z, network hardening, and surrounding infrastructure are explicitly outside the base system scope.
- Detection thresholds are configuration-driven rather than managed through an administrative control plane.

## Current Design Tradeoffs

| Tradeoff | Benefit | Cost |
| --- | --- | --- |
| Modular monolith | Simpler deployment and easier feature coordination | Limits horizontal separation of concerns at higher scale |
| SQLite support | Fast local setup and low operational overhead | Unsuitable for larger datasets and stronger production demands |
| File-based replay model | Straightforward ingestion and testing workflow | No realtime feed support |
| Rule-based anomaly detection | Transparent and explainable detection behavior | Coverage is limited to modeled conditions |
| Per-point transaction isolation after fixes | Better reliability and less data loss from bad records | Lower throughput than coarser transaction batching |
| Database-backed cooldown and historical storage | Better persistence and multi-instance readiness than in-memory state | Adds database dependency to core alerting behavior |
