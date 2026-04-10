# AegisAIS — Trust Kit

> Procurement-ready security and architecture documentation for institutional buyers.

## Architecture Overview

```
┌──────────────────────┐    ┌──────────────┐    ┌───────────────┐
│ AIS / S-AIS / Import │───▶│  Ingestion   │───▶│  Detection    │
│ Feeds + Migration    │    │  Pipeline    │    │  Engine       │
│ Adapters             │    │  (FastAPI)   │    │  (Rules + ML) │
└──────────────────────┘    └──────────────┘    └───────┬───────┘
                                                         │
                       ┌──────────────┐    ┌─────────────▼─────────────┐
                       │ PostgreSQL   │◀───│ Alerts / Incidents /      │
                       │ + PostGIS    │    │ Audit / Billing / Sharing │
                       └──────────────┘    └─────────────┬─────────────┘
                                                         │
                       ┌──────────────┐    ┌─────────────▼─────────────┐
                       │ Redis        │◀───│ WebSocket + BFF Policy /  │
                       │ Cache / RL   │    │ JWT / Classification Gate │
                       └──────────────┘    └───────────────────────────┘
```

## Detection Rules

| Rule                   | Description                                                    | Threat Detected                             |
| ---------------------- | -------------------------------------------------------------- | ------------------------------------------- |
| Teleportation          | Vessel reports position physically impossible given speed/time | AIS spoofing, GPS manipulation              |
| Turn Rate Anomaly      | Reported turn rate exceeds physical capability                 | Data injection                              |
| Position Validity      | Coordinates outside valid range or on land                     | Malformed/spoofed data                      |
| Acceleration Check     | Speed change exceeds vessel class capability                   | Spoofing, equipment malfunction             |
| Heading/COG Divergence | Heading and course-over-ground diverge beyond threshold        | Navigation data inconsistency               |
| Geofence Breach        | Vessel enters restricted or monitored zone                     | Infrastructure threat, regulatory violation |
| Identity Consistency   | MMSI/IMO/callsign contradictions across messages               | Identity spoofing                           |

## Data Residency

- Deployment region is customer-controlled at the infrastructure layer.
- No application behavior requires cross-region data transfer by default.
- Customer-controlled key management and BYOK remain deployment/infrastructure decisions, not an application-layer guarantee.
- Encryption at rest and TLS posture depend on the selected runtime environment and infrastructure controls.

## Security Posture

- API operator and collaboration routes are authenticated with role-aware access control.
- Sharing routes require authenticated analyst context and derive source organisation from the caller.
- Shared COP access requires authenticated viewer context.
- Alert status WebSocket broadcasts are org-scoped for tenant-aware payloads.
- BFF supports Bearer JWT validation with issuer, audience, and JWKS verification; production expects cryptographic verification.
- BFF policy middleware can enforce minimum classification and releasability tags on sensitive routes.
- Alert export endpoints enforce explicit bounds instead of unbounded bulk export behavior.
- Prometheus metrics and structured logs are present for operational monitoring.
- Dependency and container assurance remain partially implemented and should be represented through the evidence pack rather than assumed here.

## Evidence Highlights

- Audit and control evidence pack: `docs/SECURITY_EVIDENCE_PACK.md`
- Security and compliance control matrix: `docs/security/SECURITY_AND_COMPLIANCE.md`
- Current platform audit baseline: `docs/AEGISAIS_AUDIT_2026-04-07.md`
- Current user-flow baseline: `docs/USER_FLOW_AUDIT_2026-04-07.md`
- Focused validation command for current collaboration and tenant controls:

```bash
cd apps/api && ./.venv/bin/python -m pytest tests/test_sharing_api.py tests/test_websocket_auth.py tests/test_interoperability.py -q
```

Current focused validation result at last review: `18 passed, 1 xfailed`.

## Compliance Positioning

| Standard                      | Relevance                                                                                                |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| NIS2 Directive                | Maritime transport is a covered sector; AegisAIS provides monitoring and incident detection capabilities |
| IMO Resolution A.1106(29)     | AIS data integrity monitoring supports flag state compliance                                             |
| EU Maritime Safety Regulation | Anomaly detection supports vessel traffic monitoring requirements                                        |

Positioning note:

- AegisAIS now has stronger control evidence than older planning docs implied, but external assurance artifacts such as pen test results, ISO gap analysis, and completed IR runbooks are still open items.

## Incident Response Runbook (Summary)

1. Alert triggers in detection engine → classified by priority (P1–P4)
2. P1/P2: WebSocket push to operator dashboard + webhook to SOC integration
3. Operator acknowledges alert, creates incident record
4. Investigation via track replay and historical analysis
5. Incident resolved → audit log entry with resolution details
6. Monthly report generated with alert statistics and trend analysis

## Current Limits

- Live feed readiness remains environment-dependent where external provider credentials are absent.
- Entitlement enforcement exists, but a single authoritative cross-surface entitlement decision plane is still being consolidated.
- Cross-org sharing is authenticated and tenant-derived, but is still payload-backed rather than persisted as first-class collaboration records.
