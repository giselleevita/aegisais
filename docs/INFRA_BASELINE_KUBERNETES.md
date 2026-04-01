# Infrastructure Re-evaluation and Kubernetes Baseline

## Current Topology Assessment

### Strengths

- Clear service split across API, BFF, web, and background workers.
- Existing health checks and Prometheus instrumentation in the API and workers.
- Dockerized API/BFF with deterministic startup routines.

### Reliability Risks

- The `web` service in Compose currently runs a development server (`vite dev`) rather than a production static runtime.
- API and BFF share overlapping `/v1/*` path shapes, making single-host ingress routing ambiguous.
- Workers have heartbeat-based health in Compose but no Kubernetes-native equivalents were previously defined.

### Cost Risks

- No autoscaling policy existed for API/BFF, increasing overprovisioning or saturation risk.
- No environment overlays were present for staging vs production density.
- Stateful dependencies (PostgreSQL, Redis) are tightly coupled to local Compose patterns.

## Implemented High-Value Fixes

1. Added a production-ready web container image using multi-stage build and Nginx static serving.
2. Added Kubernetes base manifests for API, BFF, web, and each worker role.
3. Added HPA and PDB controls for core online services.
4. Added ingress routing with host split to avoid API/BFF route collisions.
5. Added Prometheus scrape and alert ConfigMaps aligned with existing rule names.
6. Added staging and production overlays for low-risk progressive rollout.
7. Added image build and Kubernetes promotion workflows in GitHub Actions.
8. Added managed dependency profile for external PostgreSQL/Redis endpoints.
9. Added optional Argo Rollouts canary scaffolding for API and web.

## Production Baseline

- Namespace isolation: `aegisais`
- Stateless app tier: API, BFF, web, workers
- Ingress tier: NGINX Ingress Controller
- Observability: Prometheus scraping `/metrics` + alert rules
- Availability controls: readiness/liveness probes, HPAs, PDBs
- Secrets: externalized in Kubernetes Secret (template provided, no live values committed)

## Rollout Strategy

1. Build and publish images with immutable tags.
2. Create secret from `infra/k8s/base/secret.example.yaml` with real credentials.
3. Deploy staging overlay and run smoke + functional checks.
4. Promote same image set to production overlay.
5. Verify SLOs and worker lag metrics before widening traffic.

Promotion automation is available via `.github/workflows/promote-k8s.yml` with environment and profile selection.
If rollout status checks fail, the workflow automatically executes `kubectl rollout undo` for API, BFF, web, and worker deployments.

## Rollback Paths

- Fast rollback for app tier:
  - `kubectl rollout undo deploy/api -n aegisais`
  - `kubectl rollout undo deploy/bff -n aegisais`
  - `kubectl rollout undo deploy/web -n aegisais`
- Revision-specific rollback:
  - `kubectl rollout history deploy/api -n aegisais`
  - `kubectl rollout undo deploy/api --to-revision=<N> -n aegisais`

## Minimal-Disruption Migration Path From Compose

1. Keep Docker Compose for local development workflows.
2. Build and deploy only app tier to Kubernetes first, while using managed or pre-existing PostgreSQL/Redis endpoints.
3. Migrate ingress and TLS termination to cluster ingress.
4. Shift background workers after API stability is confirmed.
5. Decommission Compose runtime in non-local environments.

## Managed Dependency Profile

Use `infra/k8s/profiles/managed-deps` when database and cache are managed services.

- Secret contract: `infra/k8s/profiles/managed-deps/secret.contract.yaml`
- Readiness gate: API endpoint `/v1/health/ready` now returns 503 if DB or Redis connectivity is degraded.

## Progressive Delivery (Optional)

Use `infra/k8s/canary/argorollouts` only when Argo Rollouts CRDs/controller are installed.

## Next Improvements

1. Add CI pipeline for image build, signing, and overlay deploy promotion.
2. Add canary rollout policy (Argo Rollouts or equivalent) for API and web.
3. Add centralized logs (Loki/ELK/OpenSearch) and SLO dashboards.
4. Add backup/restore runbooks for managed PostgreSQL/Redis.
