# Global Geoint Platform Vision

## Product Thesis

AegisAIS evolves from AIS anomaly tooling into a modular **global geospatial intelligence workbench**: a 3D globe + layer catalog + explainable risk pipeline built for analysts who need provenance, confidence, and operational trust.

## Mission Outcomes

- Fuse multi-domain observations (maritime, aviation, ports, infrastructure, partner feeds).
- Provide explainable alerts and incident workflows with full evidence and auditability.
- Support Live + Replay operations for training, exercises, and deterministic validation.

## Guardrails

- No fake “live” claims: mark data as observed, derived, inferred, simulation, or partner-only.
- No live submarine tracking unless lawful partner feed exists; otherwise inferred subsurface zones only.
- Dataset license constraints are first-class runtime policy.
- Provider tokens/secrets never exposed to client.

## Capability Pillars

1. **Layer Registry**: governed catalog with licensing, access, confidence, provenance.
2. **3D Workbench**: Cesium globe, timeline, inspector, query/search.
3. **Contract Core**: shared schemas for entity/observation/track/event/alert/incident.
4. **Detection + Incidents**: explainable fused rules and evidence-centric case lifecycle.
5. **Compliance by Design**: RBAC/tenant boundaries, export audit logs, provenance display.

## Near-Term Vertical Slice

- Flights live (OpenSky adapter with quota/cache mapping).
- Ports reference (WPI + UN/LOCODE import).
- Subsea cables placeholder/import path (license-gated).
- Cable proximity fused alert -> incident with explainability.
