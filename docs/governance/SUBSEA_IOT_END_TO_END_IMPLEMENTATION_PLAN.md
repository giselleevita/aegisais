# Subsea IoT End-to-End Implementation Plan

**Version:** 1.0 | **Date:** 2026-04-10 | **Status:** Active

This plan converts the current AegisAIS detection-to-decision positioning into an executable implementation roadmap for an IoT-enabled subsea infrastructure monitoring solution.

It is intended to answer a specific product gap:

- current strength: end-to-end maritime anomaly detection, evidence generation, interoperability, and operator handoff
- required next state: real sensor-connected, edge-capable, multi-sensor subsea infrastructure monitoring

---

## 1 Target Outcome

The target system is an end-to-end subsea infrastructure monitoring platform that can:

1. ingest vessel, sensor, and edge telemetry from live sources
2. correlate that telemetry with cable corridors, landing stations, and protected zones
3. detect suspicious or abnormal activity using rules plus learned behavior models
4. generate evidence-backed alerts with device, asset, and sensor provenance
5. disseminate operational outputs into downstream NATO or partner environments
6. operate in sovereign or disconnected environments with edge buffering and secure device trust

---

## 2 Scope Boundary

This roadmap intentionally covers the software and data layer required for an end-to-end detection-to-decision workflow.

In scope:

- sensor ingestion and normalization
- device and gateway trust management
- cable and infrastructure asset modeling
- rules, fusion, scoring, and prioritization
- evidence generation and interoperable dissemination
- operator workflow and response handoff
- pilot evidence and deployment proof

Out of scope for this programme increment:

- physical interdiction or repair capability
- sovereign satellite ownership
- seabed hardware manufacturing
- military response execution

---

## 3 Current Gaps To Close

| Gap                              | Current State                                                  | Required State                                               |
| -------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------ |
| Live field-device ingest         | API and feed integrations exist; direct device layer is absent | Real device and gateway telemetry enters platform            |
| Edge operation                   | Centralized stack only                                         | Store-and-forward edge gateway with health telemetry         |
| Device identity and trust        | No device registry or certificate lifecycle                    | Managed device identities, keys, and revocation              |
| Industrial / telemetry protocols | AIS/API oriented                                               | MQTT plus streaming device telemetry support                 |
| Infrastructure asset model       | Geofences and corridor logic exist                             | Cable segments, landing stations, sensors, maintenance zones |
| Multi-sensor fusion              | AIS-centric                                                    | AIS + sensor + edge + operator context fusion                |
| Automated response workflow      | Alerts and exports exist                                       | Incident orchestration and operator handoff playbooks        |
| IoT field proof                  | Repo-backed evidence only                                      | Pilot evidence with live gateways or representative devices  |

---

## 4 Workstreams

### WS-1: Asset and Infrastructure Model

**Goal:** Represent cable infrastructure, attached sensors, and operating context as first-class entities.

**Additions:**

- new infrastructure asset model for cable segments, landing stations, sensor nodes, patrol zones, and maintenance windows
- relation model between assets, geofences, alerts, and incidents
- zone policy model defining expected traffic patterns and escalation thresholds

**Primary file targets:**

- `apps/api/app/modules/assets/models.py`
- `apps/api/app/modules/assets/schemas.py`
- `apps/api/app/modules/assets/router.py`
- `apps/api/alembic/versions/*`
- `packages/contracts/schemas/Asset.schema.json`
- `packages/contracts/schemas/SensorNode.schema.json`

**Acceptance criteria:**

- cable segments and landing stations can be stored, queried, and linked to alerts
- alerts can reference both vessel and asset context
- maintenance or permitted-work windows can suppress false positives by policy

### WS-2: IoT Device and Gateway Layer

**Goal:** Introduce a device registry and gateway abstraction for field telemetry.

**Additions:**

- device registry for gateways, sensors, and collectors
- device identity, key material reference, status, firmware version, and revocation state
- gateway heartbeat and health reporting
- metadata model for connectivity profile and location

**Primary file targets:**

- `apps/api/app/modules/iot/models.py`
- `apps/api/app/modules/iot/schemas.py`
- `apps/api/app/modules/iot/router.py`
- `apps/api/app/modules/iot/service.py`
- `packages/contracts/schemas/Device.schema.json`
- `packages/contracts/schemas/DeviceHeartbeat.schema.json`

**Acceptance criteria:**

- devices can be registered, disabled, rotated, and queried
- gateways report health and last-seen timestamps
- alerts can include originating device or gateway provenance

### WS-3: Telemetry Ingestion Protocols

**Goal:** Accept real field telemetry rather than only upstream API feeds.

**Additions:**

- MQTT ingestion service for sensor and gateway events
- normalized telemetry envelope for non-AIS sources
- NMEA streaming over TCP/UDP for live receivers
- replay-safe ingest path with idempotent event keys

**Primary file targets:**

- `apps/api/app/infrastructure/iot/mqtt_consumer.py`
- `apps/api/app/infrastructure/iot/telemetry_normalizer.py`
- `apps/api/app/modules/itdae/ingestion/stream.py`
- `apps/api/app/services/pipeline.py`
- `packages/contracts/schemas/SensorReading.schema.json`
- `packages/contracts/schemas/TelemetryEnvelope.schema.json`

**Acceptance criteria:**

- the platform can ingest MQTT sensor messages and convert them into canonical telemetry
- streaming NMEA receiver data can enter the same detection pipeline
- duplicated gateway retransmits do not create duplicate alerts or events

### WS-4: Edge Gateway and Offline Operation

**Goal:** Support disconnected and degraded environments.

**Additions:**

- edge agent profile with local queueing and store-and-forward behavior
- retry and backfill after connectivity loss
- signed batch upload path from remote gateways
- edge configuration package for sovereign and air-gapped deployments

**Primary file targets:**

- `apps/api/app/modules/iot/edge_ingest.py`
- `apps/api/app/modules/iot/edge_sync.py`
- `docs/security/AIR_GAPPED_DEPLOYMENT.md`
- `docs/architecture/INFRA_BASELINE_KUBERNETES.md`
- `infra/docker/docker-compose.yml`

**Acceptance criteria:**

- an edge gateway can queue telemetry while disconnected and replay it when reconnected
- replayed edge batches preserve ordering and provenance
- air-gapped deployment guidance includes sensor and gateway onboarding steps

### WS-5: Sensor Fusion and Detection

**Goal:** Correlate AIS and non-AIS observations around subsea assets.

**Additions:**

- fusion layer joining vessel tracks, sensor readings, asset context, and operator annotations
- sensor-aware rules for cable-zone disturbance, unexpected environmental change, sensor tamper, and corroborated vessel proximity
- learned baselines for pattern-of-life around cable zones

**Primary file targets:**

- `apps/api/app/detection/iot_fusion.py`
- `apps/api/app/detection/spoofing.py`
- `apps/api/app/detection/ml_scoring.py`
- `apps/api/app/modules/assets/service.py`
- `apps/api/tests/test_iot_fusion.py`

**Acceptance criteria:**

- alerts can be produced from combined vessel and sensor evidence
- cable-zone alerts include asset, device, and timing context
- false positives are reduced by maintenance-window and multi-signal logic

### WS-6: Operator Workflow and Response Handoff

**Goal:** Turn detections into operationally usable workflows.

**Additions:**

- incident templates for subsea asset threats
- escalation rules by asset criticality and evidence confidence
- automated handoff packages for TAK / CoT / NFFI plus partner-safe summaries
- operator dashboard views for assets, sensors, and current cable-risk picture

**Primary file targets:**

- `apps/api/app/modules/incidents/service.py`
- `apps/api/app/modules/interop/*`
- `apps/web/src/features/`
- `apps/web/src/aml/pages/`
- `docs/operations/DEMO_GUIDE.md`

**Acceptance criteria:**

- operators can view active cable assets, related sensors, and current alerts in one workflow
- incidents can be created with a complete evidence bundle
- downstream interoperable exports include cable-asset context where appropriate

### WS-7: Security, Device Trust, and Compliance

**Goal:** Make the IoT expansion procurement-safe.

**Additions:**

- per-device trust policy and certificate lifecycle documentation
- device audit events for registration, rotation, disable, and sync
- gateway software supply-chain evidence and signing policy
- secure handling of offline sensor imports in restricted environments

**Primary file targets:**

- `docs/security/SECURITY_EVIDENCE_PACK.md`
- `docs/security/SECURITY_AND_COMPLIANCE.md`
- `docs/security/SUPPLY_CHAIN_ASSURANCE.md`
- `scripts/check_audit_coverage.py`
- `apps/api/tests/test_iot_audit.py`

**Acceptance criteria:**

- device lifecycle operations are audited
- IoT-specific trust and edge controls are reflected in the security evidence pack
- restricted or sovereign deployment documentation covers field-device onboarding

### WS-8: Pilot Evidence and TRL Uplift

**Goal:** Move from lab-only credibility to relevant-environment proof.

**Additions:**

- pilot pack for live gateway or representative device trial
- KPI definitions for device uptime, alert lead-time, edge sync recovery, and sensor corroboration rate
- evidence package for live subsea or representative cable-zone exercise

**Primary file targets:**

- `docs/funding/FUNDING_PILOT_EVIDENCE_TEMPLATE.md`
- `docs/funding/NATO_SUBMISSION_CLOSEOUT_CHECKLIST.md`
- `docs/funding/FUNDING_ROUTE_MATRIX.md`
- `docs/operations/DEMO_GUIDE.md`

**Acceptance criteria:**

- at least one pilot template explicitly covers gateways and non-AIS sensors
- KPI package includes IoT-specific operational evidence
- TRL narrative can point to relevant-environment sensor deployment evidence

---

## 5 Delivery Phases

### Phase 0: Positioning and Contract Foundation

**Duration:** 1 week

**Deliverables:**

- final positioning update for README and bid language
- contract schemas for assets, devices, telemetry, and sensor readings
- domain documentation for the IoT-enabled target architecture

### Phase 1: Core Data and Device Model

**Duration:** 2 to 3 weeks

**Deliverables:**

- asset model
- device registry
- migrations
- CRUD and query APIs

**Exit criteria:**

- assets, sensors, and gateways are first-class entities in the platform

### Phase 2: Live Telemetry and Edge Ingest

**Duration:** 3 to 4 weeks

**Deliverables:**

- MQTT consumer
- NMEA streaming ingest
- telemetry normalization
- edge queue and sync behavior

**Exit criteria:**

- at least one real device or gateway feed reaches the canonical pipeline

### Phase 3: Fusion, Rules, and Workflow

**Duration:** 3 to 4 weeks

**Deliverables:**

- multi-sensor fusion engine
- cable-specific rule set
- UI support for asset and sensor context
- operator incident handoff workflow

**Exit criteria:**

- alerts combine vessel, asset, and sensor context in one evidence record

### Phase 4: Security and Field Proof

**Duration:** 3 to 5 weeks

**Deliverables:**

- IoT trust and audit controls
- edge security evidence
- pilot evidence pack
- field or representative-environment demonstration

**Exit criteria:**

- the platform can credibly claim IoT-enabled subsea monitoring in a pilot or evaluation package

---

## 6 Suggested Build Order

1. asset model and schemas
2. device registry and audit events
3. MQTT ingest and telemetry envelope
4. edge queue and sync path
5. fusion and cable-specific detection logic
6. operator workflow and interoperable export enrichment
7. pilot package and live proof

This order is designed to avoid building UI or procurement language ahead of a working telemetry and device layer.

---

## 7 Minimum Viable IoT Expansion

The minimum credible IoT-enabled release should include all of the following:

- one device registry with health status and audit trail
- one MQTT telemetry ingest path
- one edge queue and replay mechanism
- one non-AIS sensor type linked to cable assets
- one fusion alert combining vessel and sensor evidence
- one dashboard view showing asset, sensor, and vessel context together

If any of these are missing, the platform is better described as infrastructure-aware maritime analytics rather than IoT-enabled monitoring.

---

## 8 90-Day Plan

### Weeks 1-2

- define schemas for assets, devices, heartbeats, and sensor readings
- create database migrations and base API routes
- document target architecture and deployment assumptions

### Weeks 3-5

- implement MQTT ingest and NMEA streaming ingest
- add canonical telemetry normalization and deduplication
- add gateway heartbeat and health views

### Weeks 6-8

- implement edge buffering and signed batch replay
- implement sensor-aware cable-zone rules and fusion logic
- expose asset and sensor context in operator workflows

### Weeks 9-12

- add IoT-specific audit and security evidence
- extend pilot and close-out documentation for live gateway trials
- run a representative demo or pilot and archive evidence

---

## 9 Success Criteria

This plan is complete only when:

- the platform ingests at least one real or representative field-device stream
- alerts can reference a cable asset, a vessel, and a sensor or gateway in one evidence chain
- edge replay works after disconnection without corrupting event history
- device lifecycle actions are audited and represented in the security evidence pack
- a pilot package demonstrates IoT-enabled subsea monitoring in a relevant environment

---

## 10 Canonical Related Documents

- `README.md`
- `docs/funding/NATO_FUNDABILITY_GAP_ANALYSIS.md`
- `docs/funding/NATO_SUBMISSION_CLOSEOUT_CHECKLIST.md`
- `docs/product/INTEROPERABILITY_PROFILE.md`
- `docs/security/SECURITY_EVIDENCE_PACK.md`
- `docs/security/AIR_GAPPED_DEPLOYMENT.md`
- `docs/governance/BUSINESS_LOGIC_IMPLEMENTATION_BACKLOG.md`
