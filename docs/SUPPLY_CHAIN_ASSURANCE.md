# Supply Chain Assurance

**Version:** 1.1 | **Date:** 2026-03-31 | **Status:** Active

This document operationalizes BL-016 and defines software supply-chain assurances, vulnerability policy, artifact integrity controls, and sovereign deployment reference architecture.

---

## 1 SBOM and Artifact Integrity

### 1.1 SBOM Generation

Software Bills of Materials are generated automatically on every CI push to `main` and on every pull-request merge:

| Artefact                 | Format         | Tool                     | CI Job         | Retention                  |
| ------------------------ | -------------- | ------------------------ | -------------- | -------------------------- |
| `backend-sbom.cdx.json`  | CycloneDX JSON | `anchore/sbom-action@v0` | `supply-chain` | 90 days (GitHub artifacts) |
| `frontend-sbom.cdx.json` | CycloneDX JSON | `anchore/sbom-action@v0` | `supply-chain` | 90 days (GitHub artifacts) |

Both SBOMs are generated before downstream build jobs may run (`needs: supply-chain` dependency gate).

### 1.2 Provenance Attestation

SLSA build provenance attestation is generated for both SBOM artefacts using `actions/attest-build-provenance@v1`. This creates a verifiable link between the CI run identity and the produced artefacts. Downstream consumers can verify authenticity with:

```bash
gh attestation verify backend-sbom.cdx.json --repo <org>/aegisais
```

The attestation covers: commit SHA, workflow reference, runner environment, and artefact digest.

### 1.3 Dependency Pinning

| Layer               | Pinning Strategy                                                                                                                           |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Python (API)        | `requirements.lock` and `requirements-dev.lock` generated with `pip-compile`; checked into repo and validated in CI (`check_lockfiles.sh`) |
| Node.js (BFF / Web) | `package-lock.json` checked in; `npm ci` used in all CI steps (deterministic install)                                                      |
| Docker base images  | Pinned by digest in Dockerfiles (production builds)                                                                                        |
| GitHub Actions      | Actions pinned by commit SHA where policy allows                                                                                           |

---

## 2 Vulnerability Policy

### 2.1 SLA Table

| Severity | Remediation Target | CI Behavior                                      | Escalation                              |
| -------- | ------------------ | ------------------------------------------------ | --------------------------------------- |
| Critical | 48 hours           | CI fails immediately (`pip-audit` + `npm audit`) | Immediate incident review; CTO notified |
| High     | 7 days             | CI fails at `--audit-level=high`                 | Weekly security checkpoint              |
| Medium   | 30 days            | Logged; advisory in PR                           | Monthly backlog review                  |
| Low      | Best effort        | Advisory only                                    | Quarterly hygiene cycle                 |

### 2.2 CI Enforcement

```yaml
# Python: backend vulnerability gate
- name: Backend vulnerability gate
  run: pip-audit -r requirements.lock --ignore-vuln CVE-2024-23342

# Node.js: frontend vulnerability gate
- name: Frontend vulnerability gate
  run: npm audit --audit-level=high
```

Both gates run in the `supply-chain` job, which is a prerequisite for `backend` and `frontend` jobs. A failing gate blocks all downstream jobs.

### 2.3 Known Accepted Exceptions

| CVE            | Package        | Reason                                                               | Review Date    |
| -------------- | -------------- | -------------------------------------------------------------------- | -------------- |
| CVE-2024-23342 | ecdsa (Python) | No exploitable path in our ECDSA usage pattern; upstream fix pending | 2026-Q2 review |

Any new exception requires documented justification, explicit `--ignore-vuln` flag, and a named review date.

---

## 3 Sovereign Deployment Reference Architecture

### 3.1 Deployment Profiles

AegisAIS supports three deployment sovereignty tiers:

| Tier                        | Profile                                   | Data Residency        | Tenant Isolation                            | Notes                                   |
| --------------------------- | ----------------------------------------- | --------------------- | ------------------------------------------- | --------------------------------------- |
| Cloud-hosted (multi-tenant) | `overlays/staging`, `overlays/production` | Provider-default      | Database-level org scoping (BL-001, BL-002) | Standard SaaS                           |
| EU-sovereign                | `profiles/sovereign-eu`                   | EU region-constrained | Database + namespace isolation              | Disables cross-region replay by default |
| UK-sovereign                | `profiles/sovereign-uk`                   | UK region-constrained | Database + namespace isolation              | Separate namespace; no EU data egress   |

### 3.2 EU Sovereign Profile (`profiles/sovereign-eu`)

Applies:

- Kubernetes namespace annotation marking EU residency intent (`aegisais.io/data-region: eu`)
- ConfigMap flag `REPLAY_DISABLED=true` — prevents historical re-ingestion from non-EU sources
- Sovereignty marker `SOVEREIGNTY_PROFILE=eu` — referenced by audit and compliance scripts

```bash
kubectl diff -k infra/k8s/profiles/sovereign-eu
kubectl apply -k infra/k8s/profiles/sovereign-eu
```

### 3.3 UK Sovereign Profile (`profiles/sovereign-uk`)

Applies:

- Separate Kubernetes namespace (`aegisais-uk`) for physical workload isolation
- ConfigMap flag `SOVEREIGNTY_PROFILE=uk`
- Replay disabled by default; re-enabled only with explicit operator approval

```bash
kubectl diff -k infra/k8s/profiles/sovereign-uk
kubectl apply -k infra/k8s/profiles/sovereign-uk
```

### 3.4 Tenant Data Isolation Controls

| Control               | Implementation                                                                   | Evidence                     |
| --------------------- | -------------------------------------------------------------------------------- | ---------------------------- |
| Row-level org scoping | `organisation_id` on all vessel, alert, incident tables; enforced in ORM queries | `test_org_scope.py`          |
| API-level filtering   | All list endpoints filter by authenticated org; no cross-tenant data returned    | `test_alerts_vessels_api.py` |
| Redis key namespacing | Rate limiter uses `{prefix}:{org_id}:{route}` key pattern                        | `rateLimiter.ts`             |
| Audit trail isolation | All audit events include `organisation_id`; no cross-tenant audit leakage        | `test_alert_worker_audit.py` |

---

## 4 Artifact Signing Roadmap

| Artefact         | Current State                               | Target                                          |
| ---------------- | ------------------------------------------- | ----------------------------------------------- |
| SBOM files       | SLSA provenance attestation (GitHub-native) | Cosign signature + Rekor transparency log entry |
| Container images | Not signed                                  | Cosign image signing in `images.yml` pipeline   |
| Release tarballs | Not signed                                  | `gh release create` with SLSA provenance        |

Container image signing will be added in the next programme increment using `sigstore/cosign-installer` in the `images.yml` workflow.

---

## 5 Open Gaps

| Gap                         | Impact                                                                 | Target                            |
| --------------------------- | ---------------------------------------------------------------------- | --------------------------------- |
| Container image signing     | Medium — supply-chain verification incomplete without image signatures | Next CI increment                 |
| Cosign + Rekor SBOM signing | Low — SLSA attestation already present; Rekor log adds transparency    | Next CI increment                 |
| Tarball release provenance  | Low                                                                    | On first public release cut       |
| SBOM retention > 90 days    | Low — procurement reviews may need longer retention                    | Configure artifact storage policy |

---

## 6 Evidence Pointers

| Artefact                                 | Location                                                       |
| ---------------------------------------- | -------------------------------------------------------------- |
| CI workflow (SBOM + vulnerability gates) | `.github/workflows/ci.yml` (`supply-chain` job)                |
| Sovereign EU profile                     | `infra/k8s/profiles/sovereign-eu/`                             |
| Sovereign UK profile                     | `infra/k8s/profiles/sovereign-uk/`                             |
| Kubernetes deployment overview           | `infra/k8s/README.md`                                          |
| Dependency lockfiles                     | `apps/api/requirements.lock`, `apps/api/requirements-dev.lock` |
| Org-scope isolation tests                | `apps/api/tests/test_org_scope.py`                             |
| Security control matrix                  | `docs/security/SECURITY_AND_COMPLIANCE.md`                     |
| Security evidence index                  | `docs/SECURITY_EVIDENCE_PACK.md`                               |
