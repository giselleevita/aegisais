# AegisAIS UI Functionality Alignment Audit - 2026-06-02

Scope: AML analyst console alignment with implemented platform capabilities, based on local source review, production build, and browser inspection before pulling `origin/main` on 2026-06-02.

## Executive Summary

The UI is directionally correct for AegisAIS and should not be rebuilt from scratch. The strongest product fit is the analyst-console model: triage queue, map context, alert investigation, vessel detail, watchlist, incidents, audit, ITDAE, and globe views.

The main gap is not route coverage. The gap is capability signaling: some screens imply deeper operational control than the current UI/backend contract exposes, and some degraded states previously looked like normal empty data.

After this audit, `origin/main` was pulled to `6618981`, which already includes several UI improvements, including visible alert-load error handling and broader analyst workflow changes. Treat this document as a functionality-alignment baseline and revalidate the findings against the current pulled version before starting remediation.

## Findings

### High

1. API failure state must be visibly distinct from empty operational state

- Risk: offline API, CORS/auth failure, and true zero alerts can be interpreted the same by analysts.
- Pre-pull evidence: alert and map load failures were logged but rendered as "No alerts found" or a blank default map.
- Current status after pull: partially addressed in `apps/web/src/features/alerts/components/AlertsPanel.tsx` through `describeApiFailure` and `loadError`.
- Recommendation: apply the same explicit degraded-state pattern across map, replay, incidents, sanctions, ITDAE, audit, and admin/feed status.

2. Onboarding rule configuration over-promises backend effect

- Risk: analysts may believe saved thresholds affect detection behavior when they are local browser preferences.
- Evidence: rule values are persisted to `localStorage`, not a backend rule/config endpoint.
- Recommendation: either wire this to real backend rule configuration with authorization/audit logging, or rename it as a demo/local preference panel.

3. Admin/control-plane route is not functionally mature

- Risk: primary navigation implies production control-plane capability, while the screen is explicitly a placeholder.
- Evidence: Admin page copy states zones, rules, org, and user management "will live here."
- Recommendation: move placeholder admin content behind a roadmap/development label, or expose only implemented feed-health/status controls until destructive/admin actions exist.

### Medium

4. Sanctions sync needs operational proof points

- Risk: the page reads like a complete sanctions-management workflow but exposes only sync action and summary counts.
- Recommendation: add last sync timestamp, source reachability, auth/permission state, failure details, dedupe/conflict summary, and linkages to the watchlist entries created.

5. First-run flow needs stronger guidance

- Risk: a new analyst opening an empty system sees a quiet console rather than a clear "connect data, upload, replay, or start demo" path.
- Recommendation: when no vessels/alerts exist, elevate upload/replay/demo actions instead of keeping ingest hidden in a collapsed triage detail.

6. Triage workflow is structurally strong but should remain the product center

- Strength: `Triage = alert queue + map + vessel context` matches the core AegisAIS use case.
- Recommendation: continue improving the existing analyst console rather than replacing it. Reframe navigation into:
  - Operate: triage, map, alert investigation, vessel detail.
  - Prepare: upload/replay, watchlist, sanctions, onboarding/demo data.
  - Govern: incidents, audit, admin/feed health.

## Validation Performed

- Frontend build passed with `npm run build` in `apps/web`.
- Browser inspection covered `/triage`, `/onboarding`, `/admin`, `/watchlist`, `/incidents`, and `/sanctions`.
- The local repo was then fast-forwarded from `eee38ce` to `6618981` on `main`.

## Follow-Up Recommendation

Run a second pass against the pulled version before implementing changes. Prioritize cross-route degraded states first, then correct any copy that promises backend behavior not yet implemented.
