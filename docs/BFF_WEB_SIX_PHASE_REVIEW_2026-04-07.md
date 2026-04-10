# AegisAIS BFF + Web Six-Phase Review - 2026-04-07

Scope: `apps/bff` and `apps/web` only. This is a strict read-only review after the recent backend hardening work.

## Executive Summary

- Biggest risk: the web client is still a pre-hardening consumer and does not fetch or enforce the BFF auth context, so clearance, releasability, and license controls are largely invisible in the UI.
- Biggest opportunity: one integration seam, `/v1/auth/context`, can align route gating, feature visibility, and policy-aware error messaging without large architectural churn.
- Top action: fix the immediate route mismatch for layers, then integrate authoritative auth context into the frontend before attempting any further UX expansion on the globe and policy-gated surfaces.

## Findings

### Schema

#### Missing clearance and releasability shape in frontend auth model

- Severity: High
- Why it matters: the BFF already normalizes `clearances`, `releasability`, and `licenses`, but the web state model only reasons about coarse role. That guarantees drift between backend policy and frontend affordances.
- Evidence: `apps/web/src/core/uiRole.ts`, `apps/bff/src/routes/auth.ts`, `apps/bff/src/middleware/auth.ts`
- Recommended fix: add a frontend auth-context type and retrieval path based on `/v1/auth/context`, not client-side token decoding alone.

### Routes

#### Layers route mismatch between web and BFF

- Severity: Critical
- Why it matters: the globe/layer workflow will fail before policy logic even matters because the frontend calls a different endpoint than the BFF actually exposes.
- Evidence: `apps/web/src/core/api-client.ts` calls `/v1/layers`; `apps/bff/src/routes/layers.ts` exposes `/v1/layers/manifest`
- Recommended fix: align the client to `/v1/layers/manifest` and add E2E mocking and regression coverage for that exact contract.

#### WebSocket policy exists in BFF but has no frontend pre-flight

- Severity: High
- Why it matters: the BFF correctly requires `ports:read`, `CONFIDENTIAL`, and the default releasability tag for `/v1/stream`, but the frontend attempts the flow without checking those constraints.
- Evidence: `apps/bff/src/routes/stream.ts`, `apps/web/src/features/globe/globeData.ts`
- Recommended fix: make WebSocket connection conditional on authoritative auth context and map policy denial into user-readable messaging.

### Business Logic

#### Frontend route access checks only role, not clearance or releasability

- Severity: High
- Why it matters: a user can navigate into policy-gated experiences that the BFF will reject, producing a broken operator flow instead of a guided denial.
- Evidence: `apps/web/src/aml/amlRouteMeta.ts`, `apps/web/src/aml/AmlShell.tsx`, `apps/bff/src/middleware/policy.ts`
- Recommended fix: extend route metadata to include minimum clearance and, where relevant, releasability or feature-license requirements.

#### Feature-level licenses are not represented in the frontend

- Severity: Medium
- Why it matters: buttons and flows can appear available even when the backend will deny them, which creates false affordances and operator confusion.
- Evidence: `apps/bff/src/middleware/licensing.ts`, `apps/web/src/core/api-client.ts`, `apps/web/src/aml/AmlShell.tsx`
- Recommended fix: surface the normalized license set in frontend state and bind feature visibility or disabled states to that set.

### Security

#### Frontend still trusts locally decoded JWT claims for role inference

- Severity: High
- Why it matters: the BFF does real claim validation and normalization, while the web client only base64-decodes the token to infer role. That is acceptable for cosmetic fallback only, not for policy decisions.
- Evidence: `apps/web/src/core/uiRole.ts`, `apps/bff/src/middleware/auth.ts`
- Recommended fix: treat local token decoding as non-authoritative fallback only and make `/v1/auth/context` the primary policy source.

#### Policy denials are not translated into user-meaningful errors

- Severity: Medium
- Why it matters: backend hardening is present, but the UI collapses important policy failures into generic API errors.
- Evidence: `apps/web/src/core/api-client.ts`, `apps/bff/src/middleware/policy.ts`
- Recommended fix: map `403` responses for clearance, releasability, and license failures into explicit operator-facing messages.

### Performance

#### Auth context is not cached because it does not exist yet

- Severity: Low
- Why it matters: once authoritative auth context is added, repeated route-level fetches could become noisy unless the client caches and invalidates it sensibly.
- Evidence: absence of `getAuthContext()` in `apps/web/src/core/api-client.ts`; repeated local token decoding in `apps/web/src/core/uiRole.ts`
- Recommended fix: add a small cache window and refresh trigger tied to auth changes.

### Structure

#### Web still points at the main API by default instead of the BFF policy surface

- Severity: Medium
- Why it matters: the frontend remains structurally coupled to a pre-BFF topology, which is why the new auth and policy surface is not reflected in the operator experience.
- Evidence: `apps/web/src/core/config.ts` defaults `VITE_API_BASE_URL` to `http://localhost:8001`
- Recommended fix: decide whether the BFF is the intended primary frontend entrypoint; if yes, move the web app onto that contract explicitly.

## User Flow Impact

- Globe workbench is currently at risk of hard failure because of the layers endpoint mismatch.
- Clearance- and releasability-gated experiences can currently degrade into confusing backend denials instead of explicit frontend access decisions.
- Licensed feature access is not explained to users before failure.
- Governance and operator-shell UX is stronger than before, but it is still not aligned to the actual BFF policy model.

## Validation Status

Verified via code reading:

- BFF auth middleware normalizes role, clearances, releasability, and license claims
- BFF policy middleware enforces classification and releasability on route handlers
- Web route and auth state still do not consume authoritative auth context
- Layers route mismatch is present in the current code

Verified via validation commands:

- `cd apps/bff && npm run lint && npm test` → passed
- `cd apps/web && npm run lint` → passed

Not verified in this review:

- No live frontend-to-BFF integration run was executed
- No Playwright run was executed for the BFF/web contract gaps identified here

## Prioritized Action Plan

### Immediate fixes

- Align web layer catalogue request to `/v1/layers/manifest`
- Add matching E2E mocks for the layers manifest contract
- Introduce frontend `getAuthContext()` path and authoritative auth-context storage

### Next sprint fixes

- Add clearance-aware and releasability-aware route metadata
- Bind feature visibility and disabled states to normalized license claims
- Translate BFF policy denials into operator-meaningful error messages

### Structural follow-up

- Decide whether the frontend should target the BFF as its primary backend contract
- Remove reliance on client-side JWT decoding for anything beyond fallback display state
- Add end-to-end policy coverage for clearance, releasability, and licensed feature denial paths

## Implementation Plan

### Batch 1: Contract alignment

- Expected impact: unblocks globe/layer workflow and catches the most immediate BFF/web integration break
- Likely files: `apps/web/src/core/api-client.ts`, `apps/web/e2e/mission-workflow.spec.ts`, related E2E mocks
- Validation: web lint, E2E for globe manifest load

### Batch 2: Auth context integration

- Expected impact: gives the web app an authoritative policy source for role, clearance, releasability, and licenses
- Likely files: `apps/web/src/core/api-client.ts`, `apps/web/src/core/uiRole.ts`, new auth-context hook/store, `apps/web/src/aml/AmlShell.tsx`
- Validation: web lint, targeted integration tests, shell-level route gating scenarios

### Batch 3: Policy-aware UX

- Expected impact: aligns route visibility, feature affordances, and error messages with the hardened BFF behavior
- Likely files: `apps/web/src/aml/amlRouteMeta.ts`, `apps/web/src/aml/AmlShell.tsx`, feature pages using export, globe, and stream access
- Validation: E2E coverage for denied clearance, missing NATO tag, and missing feature license paths

## Verdict

The BFF is ahead of the web client. The backend policy surface is real and tested, but the frontend still behaves like a pre-hardening consumer. This is not a backend failure; it is a contract-alignment problem. The next wave should be frontend/BFF alignment, not more backend hardening in the same area.
