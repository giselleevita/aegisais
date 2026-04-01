# Sovereign EU Profile

Use this profile when workloads must remain aligned to EU residency and handling expectations.

## What This Profile Adds

- Annotates config for EU residency intent.
- Disables replay by default.
- Sets a sovereignty profile marker that downstream workloads and audits can reference.

## Apply

Always diff before applying to review config changes:

```bash
kubectl diff -k infra/k8s/profiles/sovereign-eu
```

Then apply:

```bash
kubectl apply -k infra/k8s/profiles/sovereign-eu
```
