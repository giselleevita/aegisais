# AegisAIS — Trust Kit

> Procurement-ready security and architecture documentation for institutional buyers.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  AIS Data    │────▶│  Ingestion   │────▶│  Detection    │
│  Sources     │     │  Pipeline    │     │  Engine       │
│  (NMEA/TCP)  │     │  (FastAPI)   │     │  (7 Rules)    │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                  │
                    ┌──────────────┐     ┌────────▼───────┐
                    │  PostgreSQL  │◀────│  Alert         │
                    │  + PostGIS   │     │  Manager       │
                    └──────────────┘     └────────┬───────┘
                                                  │
                    ┌──────────────┐     ┌────────▼───────┐
                    │  Redis       │◀────│  WebSocket     │
                    │  (Pub/Sub)   │     │  Push          │
                    └──────────────┘     └────────────────┘
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

- All data stored within EU (configurable region)
- No data transmitted outside deployment region
- Customer-controlled encryption keys (BYOK supported for Fleet tier)
- PostgreSQL encryption at rest (AES-256) and in transit (TLS 1.3)

## Security Posture

- Application deployed as read-only containers with non-root execution
- All API endpoints authenticated (JWT + API key)
- Rate limiting on all public endpoints
- Security headers enforced (CSP, HSTS, X-Frame-Options)
- Prometheus metrics for operational monitoring (no PII in metrics)
- Structured logging with no sensitive data exposure (StructLog)
- Dependency scanning via GitHub Dependabot

## Compliance Positioning

| Standard                      | Relevance                                                                                                |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| NIS2 Directive                | Maritime transport is a covered sector; AegisAIS provides monitoring and incident detection capabilities |
| IMO Resolution A.1106(29)     | AIS data integrity monitoring supports flag state compliance                                             |
| EU Maritime Safety Regulation | Anomaly detection supports vessel traffic monitoring requirements                                        |

## Incident Response Runbook (Summary)

1. Alert triggers in detection engine → classified by priority (P1–P4)
2. P1/P2: WebSocket push to operator dashboard + webhook to SOC integration
3. Operator acknowledges alert, creates incident record
4. Investigation via track replay and historical analysis
5. Incident resolved → audit log entry with resolution details
6. Monthly report generated with alert statistics and trend analysis
