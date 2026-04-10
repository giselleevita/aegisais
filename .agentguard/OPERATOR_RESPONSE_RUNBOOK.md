# AgentGuard Operator Response Runbook

Use this runbook when a blocking or production validation workflow fails.

## 1. Install Source Failure

Symptoms:

- workflow fails during the install step
- errors mention missing `AGENTGUARD_INSTALL_SOURCE` or repository access

Response:

1. confirm the repository variable points to the intended tagged release
2. confirm `PRODUCTION_EVIDENCE.md` still names the same tagged release and install source
3. confirm `AGENTGUARD_REPO_TOKEN` still has read access to the private AgentGuard repository
4. rerun the workflow without changing thresholds or scenarios

## 2. External OPA Failure

Symptoms:

- production validation fails before or during the benchmark
- OPA health checks or policy decisions time out

Response:

1. inspect `results/opa.log` from the failed artifact bundle
2. confirm the policy bundle was cloned from the same tagged release as the install source
3. compare the failing run to the last passing baseline recorded in `PRODUCTION_EVIDENCE.md`
4. do not enable embedded fallback for production sign-off; fix the OPA path and rerun validation

## 3. Threshold Regression

Symptoms:

- `gate_result.json` shows `gate_failed=true`
- violations appear in the benchmark summary or executive summary

Response:

1. inspect `results/report_bundle/executive_summary.md`
2. confirm whether the failing case is adversarial-only or a benign control regression
3. if benign controls regressed, treat it as a release blocker and revert or fix the underlying change
4. if only adversarial scenarios changed, review whether the scenario corpus or thresholds need intentional revision
5. compare the new metrics against the last approved baseline in `PRODUCTION_EVIDENCE.md`

## 4. Signature Or Artifact Integrity Issue

Symptoms:

- report bundle files are missing or the manifest/signature pair is inconsistent

Response:

1. treat the run as untrusted evidence
2. rerun the workflow from the same commit and tagged AgentGuard release
3. refresh `PRODUCTION_EVIDENCE.md` only after a complete artifact set is retained
4. do not approve enforcement changes until the artifact set is complete

## 5. Rollback Trigger

Use rollback when the previously passing tagged release fails production validation and the cause is not resolved inside the current change window.

Rollback steps:

1. repoint `AGENTGUARD_INSTALL_SOURCE` to the last known-good release tag
2. rerun `agentguard-production-validation.yml`
3. update `PRODUCTION_EVIDENCE.md` to the rollback release only after the rerun passes
4. only restore the newer release after a clean production-validation run
