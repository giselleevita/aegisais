# AegisAIS Festival Evidence Sheet

## Implemented and demonstrable

- Canonical, organisation-scoped AIS and SAR observation persistence with source lineage and idempotency.
- Deterministic replay plus optional AISStream and commercial satellite-AIS provider adapters.
- AIS/SAR temporal-spatial association, unmatched SAR detection, cable proximity, and AIS-silence evidence.
- Immutable fusion events and explainable alerts with confidence, thresholds, source IDs, and processor versions.
- Isolation Forest trajectory baseline with a hashed artifact, feature manifest, empirical percentile, and rule fallback.
- Analyst layers for AIS, SAR, fused risk, cable zones, feed health, and evidence investigation.
- A bundled, attributed Natural Earth Baltic vector basemap that requires no venue network access.

## Inputs used in the Berlin scenario

| Input | Status | Licence/claim |
|---|---|---|
| AIS vessel tracks | Synthetic | Festival replay; not live |
| SAR vessel detection | Synthetic GFW-compatible record | Demonstrates adapter/fusion contract; not a satellite tasking result |
| Cable corridors | Approximate repository fixtures | Demonstration geometry; not authoritative navigation data |
| Isolation Forest training windows | Deterministically augmented synthetic normal transit | Baseline only; real-world precision not established |

## Validated by automated tests

- Contract validation, provider parsing, null-field handling, idempotent observation persistence, deterministic association, cable-risk event creation, confidence/provenance propagation, API authorization, and frontend build.
- Exact pass/fail results must be taken from the current CI run or preflight report; this document does not substitute for test output.

## Not yet field validated

- Operational false-alert rate, cross-region generalization, sustained live-feed performance, raw SAR image inference, commercial RF geolocation, or military receiver interoperability.
- The product does not infer hostile intent and does not autonomously task sensors or effectors.

## Requested pilot

A 6–8 week Baltic or North Sea operator pilot with licensed AIS/SAR inputs, agreed infrastructure zones, recorded analyst dispositions, external CoT/NFFI validation, and measured alert latency and false-alerts per vessel-hour.
