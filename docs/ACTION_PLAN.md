# Action Plan

## Immediate Fixes (0-2 weeks)

| Action | Why It Matters | Expected Outcome |
| --- | --- | --- |
| Harden the existing authentication model and deploy behind stronger boundary controls | Auth exists in code, but production-grade secret management and surrounding controls are still incomplete | Reduce the gap between code-level auth and production-ready access control |
| Standardize PostgreSQL for operational environments | The documentation clearly recommends PostgreSQL for large datasets and production-style use | Reduce scale risk and remove ambiguity around unsupported SQLite usage in serious deployments |
| Establish backup and restore procedures | Backup strategy is listed as a production requirement but not a delivered control | Create a minimum viable recovery posture for database-backed operations |
| Turn cleanup into a scheduled operational task | Cleanup exists only partially and is not scheduled | Control database growth and improve long-run reliability |
| Add baseline monitoring and error tracking | Monitoring and alerting gaps are repeatedly called out | Improve issue detection, operator awareness, and support readiness |

## Stabilization (30 days)

| Action | Why It Matters | Expected Outcome |
| --- | --- | --- |
| Add backend integration tests | Unit tests alone do not validate the full workflow | Improve confidence in upload, replay, alerting, export, and track retrieval workflows |
| Add end-to-end workflow testing for the frontend | Analyst workflows are central to product value | Reduce regressions in alert review, filtering, vessel details, and export |
| Add performance and load testing | Current throughput guidance is not backed by test evidence | Establish real capacity baselines and deployment envelopes |
| Formalize access logging for exports and sensitive endpoints | Security guidance recommends monitoring this access | Improve auditability and operational traceability |
| Consolidate operational documentation | Source materials span multiple maturity states and operating assumptions | Give engineering and operations teams one authoritative operating reference |

## Structural Refactor (60 days)

| Action | Why It Matters | Expected Outcome |
| --- | --- | --- |
| Add an administrative model for threshold management | Thresholds are currently config-file driven | Improve control, change governance, and operational tuning |
| Strengthen observability beyond basic health checks | Health endpoints alone are not sufficient for production support | Create actionable runtime visibility for incidents and scaling |
| Formalize retention and archive policy | Storage lifecycle is currently under-defined | Improve storage control, compliance posture, and recovery clarity |
| Define system-level threat model for the deployed environment | Security policy explicitly recommends it | Align deployment controls with actual threat boundaries and data handling risk |
| Cleanly separate prototype-only assumptions from production operating guidance | The system is explicitly a research and operations tool, not a complete platform | Reduce deployment ambiguity for new teams and due diligence reviewers |

## Scale Readiness (90 days)

| Action | Why It Matters | Expected Outcome |
| --- | --- | --- |
| Validate PostgreSQL-backed large-dataset processing with benchmark evidence | Current scale posture relies on recommendations rather than measured proof | Produce deployment-ready evidence for throughput, latency, and storage behavior |
| Build a realtime ingestion roadmap if live monitoring is required | Realtime AIS feed support is not implemented | Clarify whether the platform remains file-based or evolves into a live operational system |
| Reassess shared-state architecture for multi-instance operation | The fix summary already identifies prior singleton-state issues and suggests shared infrastructure options | Prepare the platform for more resilient and scalable deployment patterns |
| Expand analyst workflow analytics and reporting only after operational hardening | Feature expansion before hardening increases support risk | Preserve delivery focus on production readiness rather than surface-area growth |
| Complete operational readiness review | Current material identifies multiple deployment gaps | Produce a go or no-go decision package for broader deployment |

## Feature Freeze Recommendations

- Freeze net-new analyst features until authentication, backup, monitoring, and integration testing are in place.
- Defer non-essential UX work such as dark mode and keyboard shortcuts until the operational baseline is stable.
- Treat realtime AIS feed support as a strategic product decision, not an opportunistic feature add.
- Avoid additional export or integration surface area until access control and audit logging are established.

## Takeover Readiness Checklist

- Production deployment model documented
- PostgreSQL operating standard defined
- Backup and restore procedure documented and tested
- Cleanup and retention jobs scheduled
- Authentication and authorization boundary defined
- Monitoring and error tracking active
- Backend integration tests in place
- Frontend end-to-end workflow tests in place
- Performance baseline documented
- Export governance and access logging defined
- Threshold management process documented
- Threat model completed for the deployed environment
