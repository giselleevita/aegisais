# AegisAIS — Service Level Agreement

## Availability

| Metric                | Target        | Measurement                                                         |
| --------------------- | ------------- | ------------------------------------------------------------------- |
| Platform Uptime       | 99.9% monthly | Excluding scheduled maintenance (max 4h/month, announced 72h ahead) |
| Data Ingestion Uptime | 99.95%        | AIS message processing pipeline availability                        |

## Alert Delivery

| Alert Priority                                         | Delivery Target             | Channel                          |
| ------------------------------------------------------ | --------------------------- | -------------------------------- |
| P1 — Critical (geofence breach, AIS spoofing detected) | < 10 seconds from detection | WebSocket push + webhook + email |
| P2 — High (anomaly cluster, watchlist match)           | < 30 seconds from detection | WebSocket push + webhook         |
| P3 — Medium (single rule trigger)                      | < 60 seconds from detection | Dashboard + webhook              |
| P4 — Informational (track deviation)                   | < 5 minutes                 | Dashboard only                   |

## Incident Response

| Severity                  | Response Time            | Resolution Target  |
| ------------------------- | ------------------------ | ------------------ |
| P1 — Service down         | 30 minutes               | 4 hours            |
| P2 — Degraded performance | 2 hours                  | 8 hours            |
| P3 — Non-critical issue   | 8 hours (business hours) | 5 business days    |
| P4 — Enhancement request  | 5 business days          | Next release cycle |

## Data Retention

| Data Type               | Retention Period                     |
| ----------------------- | ------------------------------------ |
| Raw AIS messages        | 90 days (configurable)               |
| Processed track history | 12 months (add-on: extended archive) |
| Alerts and incidents    | 24 months                            |
| Audit logs              | 36 months (immutable)                |

## Exclusions

- Scheduled maintenance windows
- Force majeure events
- Third-party AIS data source outages (upstream provider responsibility)
- Customer network or firewall misconfiguration
