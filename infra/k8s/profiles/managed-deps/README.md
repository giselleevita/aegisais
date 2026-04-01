# Managed Dependency Profile

Use this profile when PostgreSQL and Redis are provided by managed services outside the cluster.

## What This Profile Changes

- Reuses the shared baseline from `infra/k8s/base`.
- Applies conservative worker rollout strategy (`Recreate`) to avoid duplicate consumers during rollout.
- Requires external dependency credentials and endpoints via `aegisais-secrets`.

## Secret Contract

Use `secret.contract.yaml` as a contract template. Required keys:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`

Optional keys:

- `TELEGEOGRAPHY_TOKEN`
- `EO_PROVIDER_TOKEN`
- `ITDAE_AIS_API_KEY`
- `ITDAE_BALTIC_BBOX`

## Dependency Readiness

API readiness now uses `/v1/health/ready`, which returns HTTP 503 when DB or Redis connectivity is degraded.

## Apply

```bash
kubectl apply -f infra/k8s/profiles/managed-deps/secret.contract.yaml -n aegisais
kubectl apply -k infra/k8s/profiles/managed-deps
```

Replace placeholder values in the secret before applying.
