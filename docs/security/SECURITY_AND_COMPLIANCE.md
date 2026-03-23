# Security and Compliance

## Enforced Controls

- Provider secrets are server-side only:
  - API/BFF read tokens from environment variables.
  - Browser payloads never include provider keys or credentials.
- Licensing gates are applied in manifest/orchestration paths:
  - restricted/non-commercial datasets are default-off and entitlement-gated.
- Evidence bundles include `schema_version` and `provenance_version`.
- Incident evidence records legal posture metadata:
  - `subsurface_tracking: not_performed`
  - explicit licensing notes for source usage constraints.
- Alert-to-incident lineage is preserved for auditability and explainability.

## Access and Tenant Boundaries

- RBAC stubs exist in API and BFF slices and are wired to authenticated roles.
- Tenant-aware access policy is represented in contracts (`access level` and scoping metadata).
- UI displays access/licence context in layer inspector and catalog.

## Audit Logging Requirements

- Audit events are required for:
  - exports/downloads
  - incident edits and status transitions
  - privileged layer access actions
- Existing audit plumbing is present; export/edit coverage is partially stubbed and called out below.

## UI Compliance Signals

- Restricted and non-commercial badges are rendered in the workbench for gated layers.
- Provenance text and confidence class/score are visible in inspector context.

## Stubbed / Pending

- Centralized legal-policy engine is not implemented yet (policy is currently rule + metadata driven).
- Automated upstream license attestation at ingest time is not fully implemented.
- Complete export/incident-edit audit event coverage is partially implemented and needs endpoint-level completion.

## Blocked

- Jurisdiction-specific legal controls for seabed/subsurface operations require formal legal counsel sign-off.
- Partner feed contracts (e.g., commercial subsea and non-commercial fishing constraints) need machine-readable entitlement sources.

## Legal Constraints

- This implementation does **not** perform direct live subsurface/submarine tracking.
- Subsurface capability is limited to inferred zones, integration stubs, and simulation/replay workflows.
- Fused detection currently uses surface-activity + cable proximity only.
