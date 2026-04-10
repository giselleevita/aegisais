# AegisAIS User Flow Audit - 2026-04-07

Scope: AML analyst console flow integrity, route safety, role transitions, operations-to-intelligence continuity, and coverage of practical user use cases.

## Executive Summary

The main AML user flows are structurally sound, but they had two classes of mismatch:

- UI state management introduced avoidable render-loop lint failures in shell and operations bootstrap.
- Flow guarantees existed conceptually, but not all critical user journeys were explicitly validated end-to-end, especially intelligence globe usage and role-based route denial.

This wave fixes the shell/operations flow mechanics, tightens backend collaboration and live-update boundaries, and expands flow validation so the implemented journeys match the intended product model.

## Core User Flows Reviewed

1. Triage flow

- Entry: `/triage`
- Actions: inspect alert queue, update status, open investigation, pivot to vessel/map.
- Outcome: alert triage remains the primary operations landing flow.

2. Investigation flow

- Entry: alert detail route.
- Actions: inspect evidence, pivot back to map/vessel context.
- Outcome: breadcrumb and route model remain aligned with analyst work.

3. Incident flow

- Entry: incidents list and incident detail.
- Actions: move from alert-derived casework to governance review.
- Outcome: operations-to-governance handoff is coherent.

4. Intelligence globe flow

- Entry: `/globe`
- Actions: choose camera preset, inspect data layers, understand live vs replay posture.
- Outcome: globe view is now a real intelligence workspace rather than a bare Cesium surface.

5. Role-restricted route flow

- Entry: direct navigation to restricted route such as `/admin`.
- Actions: route guard redirects to allowed landing route.
- Outcome: user gets deterministic redirect plus visible reason instead of silent mismatch.

6. Non-linear operator flow

- Entry: shortcuts or command palette.
- Actions: jump across operations, intelligence, governance.
- Outcome: command-driven navigation remains aligned with route access rules.

7. Supervisor sanctions flow

- Entry: `/sanctions`
- Actions: inspect current watchlist posture, sync official sanctions sources, review completion state.
- Outcome: governance-adjacent operations are available to supervisor role without requiring admin-only areas.

8. Empty-state resilience flow

- Entry: operations or incidents routes with no data returned.
- Actions: render queue/list pages under zero-alert, zero-vessel, zero-incident conditions.
- Outcome: users get stable empty-state messaging instead of broken layout or ambiguous silence.

9. Cross-org collaboration flow

- Entry: sharing routes and COP access.
- Actions: share alerts/watchlist entries with allied organisations, open shared tactical feed.
- Outcome: collaboration flow now requires authenticated user context and derives source organisation from the caller instead of a hardcoded tenant.

10. Live alert update flow

- Entry: WebSocket stream and alert status transitions.
- Actions: receive real-time alert status changes during active operations.
- Outcome: org-scoped alert updates now stay inside the caller's tenant boundary instead of broadcasting to every connected client.

## Findings

### Resolved In This Wave

1. Shell access warning was stateful rather than route-derived

- Risk: redirect feedback depended on effect-driven local state rather than navigation semantics.
- Fix: access notice now travels through route state during redirect.

2. Command palette bootstrap relied on setState inside effects

- Risk: lint violations and brittle open/reset behavior.
- Fix: palette open/close/reset behavior is now event-driven.

3. Operations recent-vessels bootstrap used effect-driven initialization

- Risk: unnecessary render pass and lint violation.
- Fix: recent vessels now initialize from local storage via lazy state initializer.

4. Globe flow lacked explicit end-to-end validation

- Risk: intelligence experience could drift from route and role model without detection.
- Fix: e2e mission workflow now covers globe preset usage and route-safe redirect behavior.

5. Supervisor and empty-state use cases were previously implicit only

- Risk: route/role model could look complete while common non-admin and no-data scenarios regress silently.
- Fix: e2e mission workflow now covers sanctions sync for supervisor role plus triage/incidents empty states.

6. Collaboration routes previously bypassed authenticated operator context

- Risk: sharing and COP flows could be invoked without the same user identity guarantees as the rest of the platform.
- Fix: sharing alert/watchlist routes now require analyst auth, COP now requires viewer auth, and source organisation is derived from the authenticated caller.

7. Live alert status updates previously ignored tenant boundaries

- Risk: real-time operational updates could leak cross-tenant state changes to unrelated connected users.
- Fix: WebSocket connections now track caller organisation and org-scoped alert status payloads are only broadcast to matching tenants.

8. Bulk export flow previously lacked an explicit upper bound

- Risk: large admin exports could degrade operational responsiveness during governance or reporting workflows.
- Fix: alert CSV/JSON export now enforces an explicit limit while preserving the existing admin export journey.

### Remaining Risks

1. Some React hook warnings still exist in unrelated pages/components.

- They are not blockers for the corrected flows here, but they weaken overall maintainability.

2. AML role source still partially depends on local storage / token inference.

- Backend `/v1/auth/context` should become the single source of truth for web bootstrap.

3. Use-case coverage is strong for analyst and admin paths, but supervisor-specific governance flow can still be validated more explicitly.

4. Collaboration flow is now authenticated, but it is still payload-backed rather than persisted entity-backed.

- Shared alert/watchlist actions should eventually produce first-class collaboration records with audit-grade provenance.

## Relevant Use Cases Covered

- Analyst triages new integrity alerts.
- Analyst pivots from queue to map and vessel context.
- Analyst opens incident detail from operations workflow.
- Admin navigates to governance areas from active mission context.
- Intelligence operator uses globe presets to reframe operational picture.
- Supervisor opens sanctions workflow and syncs official lists.
- Unauthorized user is redirected from restricted governance route with visible explanation.
- Operations and incidents pages remain usable when APIs return no rows.
- Keyboard-first operator navigates via shortcuts and command palette.
- Analyst can only invoke allied-sharing routes with authenticated org context.
- Viewer-level access is required before opening the shared COP feed.
- Real-time alert status changes stay within the correct organisation boundary.
- Governance export flow remains available but now has bounded result size.

## Recommended Next Coverage

1. Disconnected-stream workflow: explicit user messaging when WebSocket and replay status both degrade.
2. No-enabled-layer globe workflow: validate operator guidance when all intelligence overlays are disabled.
3. Deep-link restoration: direct visit to investigation or globe route after refresh with persisted UI role.
4. Mobile/compact AML flows: especially globe-to-inspector transitions on smaller screens.
5. Persisted collaboration workflow: validate shared-alert provenance once sharing moves from payload-backed to record-backed flows.

## Validation Added In This Wave

- Shell flow cleanup in `src/aml/AmlShell.tsx`
- Operations bootstrap cleanup in `src/aml/pages/OperationsPage.tsx`
- Expanded user-flow coverage in `e2e/mission-workflow.spec.ts`
- Sharing auth and org-derived collaboration flow in `apps/api/tests/test_sharing_api.py`
- Tenant-aware live alert broadcast coverage in `apps/api/tests/test_websocket_auth.py`
- Bounded alert export coverage in `apps/api/tests/test_interoperability.py`
- Focused API validation result: `18 passed, 1 xfailed`
