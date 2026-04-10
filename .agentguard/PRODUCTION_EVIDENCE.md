# AgentGuard Production Evidence

This file is the current evidence ledger for the AgentGuard production claim in AegisAIS.

It records the exact release pin, workflow runs, and retained local artifact bundle that support the current go-live decision.

## Approved Release Pin

- repository variable: `AGENTGUARD_INSTALL_SOURCE`
- current value: `git+https://github.com/giselleevita/agentguard-platform.git@v1.0.2`
- release: AgentGuard `v1.0.2`
- published release URL: `https://github.com/giselleevita/agentguard-platform/releases/tag/v1.0.2`
- published at: `2026-04-10T06:37:54Z`

## Why This Evidence Is Credible

The production-validation path is credible because it did not only produce a passing run.

It first caught a real failure on the external OPA path, that failure was investigated and fixed in AgentGuard `v1.0.2`, and the same validation path then passed on the tagged release now pinned in AegisAIS.

## Production Validation History

### Failed Run Before Fix

- workflow: AgentGuard Production Validation
- run id: `24229788792`
- result: `failure`
- URL: `https://github.com/giselleevita/aegisais/actions/runs/24229788792`
- created at: `2026-04-10T06:29:27Z`
- purpose: proved that the real external-OPA validation path was capable of rejecting a bad release candidate

### Passing Run On Approved Release

- workflow: AgentGuard Production Validation
- run id: `24230087223`
- result: `success`
- URL: `https://github.com/giselleevita/aegisais/actions/runs/24230087223`
- created at: `2026-04-10T06:38:36Z`
- release under test: `v1.0.2`
- purpose: current production sign-off run for the validated slices

## Latest Supporting Workflow Evidence

- stability sweep: run `24228514859`, `success`, `https://github.com/giselleevita/aegisais/actions/runs/24228514859`
- PR enforcement: run `24228542654`, `success`, `https://github.com/giselleevita/aegisais/actions/runs/24228542654`

## Retained Local Artifact Bundle

The latest passing production-validation artifact bundle is retained under:

- `.agentguard/last-production-validation/`

Key files:

- `.agentguard/last-production-validation/gate_result.json`
- `.agentguard/last-production-validation/summary.json`
- `.agentguard/last-production-validation/report_bundle/executive_summary.md`
- `.agentguard/last-production-validation/opa.log`

## Current Passing Metrics

From the retained passing bundle:

- blocking mode: `true`
- gate passed: `true`
- violations: `0`
- attack success rate: `0.0%`
- leakage rate: `0.0%`
- task success rate: `100.0%`
- false positive rate: `0.0%`
- p95 latency: `28.1 ms`

Executive summary status from the retained bundle:

- benign_control: `READY`
- direct_injection: `READY`
- indirect_injection: `READY`
- tool_misuse: `READY`

## Scope Of The Claim

This evidence supports a production-credible claim for the slices that were actually validated:

- sharing and COP
- export and interop review
- tenant boundary and org-scope misuse

This file does not claim universal coverage for every future AegisAIS workflow.

Any new slice must be added to the scenario corpus and must pass the same tagged-release external-OPA workflow before it should be included in the production claim.

## Renewal Rule

Update this file whenever any of the following change:

- `AGENTGUARD_INSTALL_SOURCE`
- the approved AgentGuard release tag
- the latest production-validation run used for sign-off
- the validated slice set

If this file no longer matches repository configuration or the latest retained artifact bundle, treat the production claim as stale until the evidence is refreshed.