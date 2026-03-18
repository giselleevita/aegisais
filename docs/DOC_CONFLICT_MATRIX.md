# Documentation Conflict Matrix

| New Audit Doc | Old or Conflicting Doc | Type of Conflict | Severity | Recommended Action | Disposition |
| --- | --- | --- | --- | --- | --- |
| `SYSTEM_OVERVIEW.md` | `README.md` | Product and setup overview still reference old paths and stale links | High | Update README progressively to current `apps/api` and `apps/web` layout | Update |
| `ARCHITECTURE.md` | `docs/PROJECT_STRUCTURE.md` | Legacy repository layout presented as current architecture | High | Treat `PROJECT_STRUCTURE.md` as historical and refresh or replace later | Deprecated in place |
| `ARCHITECTURE.md` | `README.md` architecture section | `backend/` and `frontend/` paths no longer match the active repo | High | Refresh architecture examples to current monorepo layout | Update |
| `RISK_REGISTER.md` | `docs/MISSING_FEATURES.md` | Historical gap analysis says auth, map, track history, alert export, and lifecycle controls are missing | High | Keep as historical context only and rely on validation plus current docs for present-state claims | Historical only |
| `RISK_REGISTER.md` | `docs/FEATURES_IMPLEMENTED.md` | Feature completion snapshot conflicts with older missing-features list and still uses legacy paths | Medium | Retain for historical implementation context, but not as authoritative state | Historical only |
| `SCALE_AND_INFRA.md` | `docs/LARGE_DATASET_GUIDE.md` | Scale guidance is still useful, but setup paths and compose references are stale | Medium | Update commands and paths while preserving the operational tuning content | Update |
| `ACTION_PLAN.md` | `docs/CODE_QUALITY.md` | `CODE_QUALITY.md` mixes aspirational quality claims with outdated structure examples | Medium | Keep as supporting historical standards doc, not a source of current-state truth | Deprecated in place |
| `SYSTEM_OVERVIEW.md` | `docs/FIXES_SUMMARY.md` | Fix history is useful but references obsolete path layout and earlier operating assumptions | Low | Keep as implementation history only | Archive later or keep historical |
| `ARCHITECTURE.md` | `.github/workflows/ci.yml` history | CI had recently pointed to legacy paths while the repo moved to `apps/*` | High | Keep workflow aligned to current layout and mention repo migration in validation notes | Update |
| `SYSTEM_OVERVIEW.md` | `docs/DEMO_GUIDE.md` | Demo guide still references old paths and older doc links | Medium | Refresh links and path references when demo workflow is next touched | Update |

## Recommended Consolidation Rules

- Treat the new audit package as the current review set.
- Treat `README.md` as the next document to refresh because it is the most visible entry point.
- Treat `PROJECT_STRUCTURE.md`, `MISSING_FEATURES.md`, `FEATURES_IMPLEMENTED.md`, `CODE_QUALITY.md`, and `FIXES_SUMMARY.md` as historical-support documents until rewritten.
- Avoid deleting historical docs until the replacement set is fully adopted in review and onboarding flows.
