# Argo Rollouts Canary Scaffolding

This folder contains optional canary rollout resources for API and web.

## Prerequisites

- Argo Rollouts CRDs and controller installed in the cluster.
- NGINX Ingress controller compatible with Argo traffic routing.
- Existing baseline services and ingress from `infra/k8s/base` already deployed.

## Apply

```bash
kubectl apply -k infra/k8s/canary/argorollouts
```

## Promote or Abort

```bash
kubectl argo rollouts get rollout api -n aegisais
kubectl argo rollouts promote api -n aegisais
kubectl argo rollouts abort api -n aegisais
```

Repeat for `web` as needed.

## Notes

- These resources are not included in the default base/overlay kustomizations.
- This keeps standard deployment paths stable while enabling progressive delivery when ready.
