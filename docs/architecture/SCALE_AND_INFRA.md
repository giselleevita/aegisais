# Scale and Infrastructure

## Infrastructure Assessment

The current system has meaningful scale-oriented features, but it is not yet an infrastructure-complete platform.

Documented strengths:

- PostgreSQL support for larger datasets
- streaming mode for large files
- batch-size tuning guidance
- database indexes for common query patterns
- replay and processing controls

Documented gaps:

- monitoring and alerting remain incomplete
- no documented backup and restore program
- no performance testing or load testing
- cleanup and retention are only partially operationalized
- realtime AIS feed support is not implemented

## Bottlenecks

| Bottleneck | Evidence | Operational Effect | Current Mitigation |
| --- | --- | --- | --- |
| SQLite for large datasets | `LARGE_DATASET_GUIDE.md` recommends PostgreSQL for datasets with millions of records | Throughput and scalability degrade as volume grows | Use PostgreSQL for large workloads |
| Large-file processing without streaming discipline | `LARGE_DATASET_GUIDE.md` and `FIXES_SUMMARY.md` highlight streaming behavior and prior memory issues | Memory pressure and unstable processing behavior | Streaming mode and chunked processing |
| Unvalidated throughput ceilings | `MISSING_FEATURES.md` says performance testing is not implemented | Capacity planning is speculative | Batch-size guidance only |
| Lack of scheduled cleanup | `MISSING_FEATURES.md` says cleanup exists but is not scheduled | Storage growth and degraded database performance | Manual or ad hoc cleanup utility |
| File-based ingestion model | `MISSING_FEATURES.md` says realtime AIS feed support is not implemented | No live operational monitoring workflow | Replay and upload model only |
| Incomplete observability | `CODE_QUALITY.md` recommends APM, error tracking, and stronger metrics collection | Slow issue detection and poor root-cause visibility | Basic health and metrics endpoints |

## Current Scaling Limits

| Area | Current Limit Indicated by Source Material |
| --- | --- |
| Database choice | SQLite is acceptable only for smaller datasets; PostgreSQL is recommended for large workloads |
| Dataset size | Large files require streaming mode and tuned batch sizes |
| Throughput certainty | No benchmark-backed limit is documented |
| Deployment resilience | Multi-instance and production-hardening expectations exceed the documented baseline |
| Realtime operations | Not supported through a live AIS feed |

## Scale Thresholds

The source material gives explicit operational thresholds and recommendations:

| Threshold | Guidance |
| --- | --- |
| Files over 50 MB | Streaming mode is automatically used |
| Less than 1 million points | Smaller batch sizes and SQLite may be acceptable |
| 1 million to 10 million points | PostgreSQL and larger batch sizes are recommended |
| More than 10 million points | PostgreSQL, larger batch sizes, and stronger database tuning are recommended |

The documentation also provides rough expected throughput ranges:

- SQLite for small datasets: approximately 1,000 to 5,000 points per second
- PostgreSQL for large datasets: approximately 10,000 to 50,000 points per second

These are operational guidance values, not results from a documented performance test program.

## Failure Modes

| Failure Mode | Source Evidence | Likely Outcome |
| --- | --- | --- |
| Database deployed on SQLite beyond intended scale | `LARGE_DATASET_GUIDE.md` | Slow processing, degraded query performance, possible operational instability |
| Cleanup not scheduled | `MISSING_FEATURES.md` | Database growth without bounded retention |
| Backup strategy absent | `README.md` production checklist | Slow recovery or data loss after failure |
| Monitoring absent or incomplete | `README.md`, `CODE_QUALITY.md`, `MISSING_FEATURES.md` | Delayed fault detection and poor incident response |
| Performance bottleneck under real load | `MISSING_FEATURES.md` notes no performance testing | Unknown saturation point and weak capacity confidence |
| Need for realtime monitoring | `MISSING_FEATURES.md` says realtime AIS feed is not implemented | Product cannot satisfy live-feed operating model |

## Observability Gaps

The current materials indicate:

- basic health checks exist
- a metrics endpoint exists
- broader observability is still incomplete

Explicit gaps documented across the source set:

- application performance monitoring
- error tracking
- richer metrics collection
- system health status beyond basic endpoint checks
- operator-facing visibility into queue state, disk state, and runtime conditions

## Reliability Posture

The documented reliability posture is mixed.

Reliability improvements already delivered:

- streaming replay no longer accumulates all points in memory
- alert cooldown state moved from memory to the database
- track store design changed away from a module-level singleton
- replay transaction boundaries were tightened to isolate bad points

Remaining reliability concerns:

- no integration test coverage
- no benchmark or stress validation
- no formal disaster recovery program
- no scheduled retention and cleanup enforcement

## Disaster Recovery Gaps

| Gap | Evidence | Consequence |
| --- | --- | --- |
| No documented backup implementation | `README.md` production checklist | Uncertain restoration path after database loss |
| No restoration testing process | No restoration workflow documented | Recovery may fail when needed |
| No retention program | `MISSING_FEATURES.md` | Poor storage hygiene and unclear recovery horizons |
| No resilience-oriented monitoring stack | `CODE_QUALITY.md`, `MISSING_FEATURES.md` | Weak incident detection and diagnosis |

## Reliability and Scale Summary

The system is capable of handling larger datasets with the right deployment posture, particularly when moved to PostgreSQL and run in streaming mode. However, the materials do not support treating the platform as scale-validated or infrastructure-complete. The main blockers are missing test evidence, incomplete monitoring, absent recovery controls, and continued dependence on operator discipline for database choice and cleanup.

## Future Architecture Evolution Path

The source materials suggest a practical evolution path:

1. Standardize PostgreSQL for production and large datasets.
2. Operationalize cleanup and retention as scheduled jobs.
3. Add integration, load, and performance testing.
4. Add monitoring, metrics, and error tracking suitable for production support.
5. Introduce realtime AIS feed support if live operations are a product requirement.
6. Consider Redis or other shared infrastructure for state coordination where multi-worker or multi-instance behavior becomes a priority.
