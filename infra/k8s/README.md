# Kubernetes Deployment Baseline

This folder provides a Kubernetes-first baseline for AegisAIS with minimal disruption to existing local Docker Compose workflows.

## Topology

- `base/`: shared production-safe defaults
- `overlays/staging/`: lower-cost staging profile
- `overlays/production/`: higher-availability profile
- `profiles/managed-deps/`: external PostgreSQL/Redis profile and secret contract
- `profiles/sovereign-eu/`: EU residency-oriented profile baseline
- `profiles/sovereign-uk/`: UK residency-oriented profile baseline
- `canary/argorollouts/`: optional progressive delivery scaffolding

## Services Mapped From Compose

- API (`apps/api`) -> `Deployment` + `Service`
- BFF (`apps/bff`) -> `Deployment` + `Service`
- Web (`apps/web`) -> `Deployment` + `Service`
- Workers (ITDAE ingestion, processing, persistence, alert) -> dedicated `Deployment` per worker role

## Observability

- Prometheus scrape and alert rule ConfigMaps are included in `base/`.
- API and workers expose `/metrics` and retain alerting compatibility with existing rule names.

## Rollout Strategy

1. Build and push images for `api`, `bff`, and `web`.
2. Apply staging overlay first.
3. Validate readiness and key SLOs.
4. Promote same image tags to production overlay.

```bash
kubectl apply -k infra/k8s/overlays/staging
kubectl rollout status deploy/api -n aegisais
kubectl rollout status deploy/bff -n aegisais
kubectl rollout status deploy/web -n aegisais
```

## Rollback Paths

- Immediate rollback to previous ReplicaSet:

```bash
kubectl rollout undo deploy/api -n aegisais
kubectl rollout undo deploy/bff -n aegisais
kubectl rollout undo deploy/web -n aegisais
```

## Sovereign Deployment Profiles

Two sovereign profiles are provided for data-residency-constrained deployments. Always `diff` before applying.

### EU Sovereign (`profiles/sovereign-eu`)

Sets:

- Namespace annotation `aegisais.io/data-region: eu`
- `REPLAY_DISABLED=true` in ConfigMap (no cross-region historical re-ingestion)
- `SOVEREIGNTY_PROFILE=eu` marker for audit scripts

```bash
kubectl diff -k infra/k8s/profiles/sovereign-eu
kubectl apply -k infra/k8s/profiles/sovereign-eu
```

### UK Sovereign (`profiles/sovereign-uk`)

Sets:

- Separate namespace `aegisais-uk` for physical workload isolation
- `SOVEREIGNTY_PROFILE=uk`
- Replay disabled by default

```bash
kubectl diff -k infra/k8s/profiles/sovereign-uk
kubectl apply -k infra/k8s/profiles/sovereign-uk
```

Full sovereignty reference architecture and tenant isolation controls are documented in `docs/SUPPLY_CHAIN_ASSURANCE.md`.

- Point-in-time rollback by revision:

```bash
kubectl rollout history deploy/api -n aegisais
kubectl rollout undo deploy/api --to-revision=<N> -n aegisais
```

## Secrets

Use `base/secret.example.yaml` as a template and apply an environment-specific secret out of band.
Do not commit live credentials.

For managed PostgreSQL/Redis, use `profiles/managed-deps/secret.contract.yaml` and deploy via:

```bash
kubectl apply -k infra/k8s/profiles/managed-deps
```

For sovereign deployment baselines, apply one of:

```bash
kubectl apply -k infra/k8s/profiles/sovereign-eu
kubectl apply -k infra/k8s/profiles/sovereign-uk
```

These profiles set residency metadata and stricter defaults that can be combined with environment overlays.

## CI/CD Integration

- Image build workflow: `.github/workflows/images.yml`
- Promotion workflow: `.github/workflows/promote-k8s.yml`

The promotion workflow supports:

- environment promotion (`staging` or `production`)
- image tag pinning
- profile selection (`base` or `managed-deps`)
- automatic rollback attempt if rollout checks fail

## Canary Rollouts

If Argo Rollouts is installed, apply optional canary resources:

```bash
kubectl apply -k infra/k8s/canary/argorollouts
```
