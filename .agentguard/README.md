# AgentGuard AegisAIS Pilots

This directory contains the current AegisAIS AgentGuard rollout slices.

Validated slices:

- workflow: authenticated alert sharing and COP access
- status: validated in both shadow and blocking mode
- purpose: keep the first enforced slice narrow and stable
- workflow: bounded alert export and interop export review
- status: validated in both shadow and blocking mode
- purpose: add a second tenant-safety slice without broadening the rollout all at once

## Files

- `config/thresholds.yaml`: initial shadow thresholds
- `config/thresholds.blocking.yaml`: stricter second-phase thresholds for validated slices
- `scenarios/aegisais-sharing-shadow.yaml`: focused sharing and COP scenario corpus
- `scenarios/aegisais-export-shadow.yaml`: focused alert export and interop export review corpus
- `scenarios/aegisais-tenant-boundary-shadow.yaml`: focused tenant-boundary and org-scope misuse corpus
- `.github/workflows/agentguard-shadow.yml`: GitHub Actions workflow that runs the benchmark and shadow gate
- `.github/workflows/agentguard-export-shadow.yml`: GitHub Actions workflow for the export and interop shadow slice
- `.github/workflows/agentguard-tenant-boundary-shadow.yml`: GitHub Actions workflow for the tenant-boundary shadow slice
- `.github/workflows/agentguard-blocking.yml`: manual blocking workflow for the second phase
- `.github/workflows/agentguard-export-blocking.yml`: manual blocking workflow for the export and interop slice
- `.github/workflows/agentguard-tenant-boundary-blocking.yml`: manual blocking workflow for the tenant-boundary slice
- `.github/workflows/agentguard-stability-sweep.yml`: scheduled and manual drift-check workflow for the validated slices
- `.github/workflows/agentguard-pr-enforcement.yml`: combined blocking workflow for validated slices on pull requests

Local-only artifacts:

- `.agentguard/last-*/`: ignored local downloads of workflow result bundles for inspection and debugging

## First Run

Use `workflow_dispatch` for the first execution.

Input:

- `agentguard_install_source`: optional full `pip install` source for AgentGuard; overrides the repository variable when set

Default behavior:

- installs AgentGuard from the repository variable `AGENTGUARD_INSTALL_SOURCE`
- uses the repository secret `AGENTGUARD_REPO_TOKEN` automatically when the source is a private GitHub clone URL
- bootstraps a baseline model into `.agentguard/models/default`
- runs the scenario set configured by the selected workflow
- writes benchmark results and a signed report bundle as workflow artifacts

Before the first run, set the AegisAIS repository variable `AGENTGUARD_INSTALL_SOURCE` to the exact install source you want the workflow to use.

If the install source points to a private GitHub repository, also set the repository secret `AGENTGUARD_REPO_TOKEN` with a token that can read that repository.

Current configured source:

```text
git+https://github.com/giselleevita/agentguard-platform.git@58995a55638a0bbe9f46a660cbc0152a98b849db
```

Accepted examples:

```text
git+https://github.com/<owner>/agentguard-platform.git@main
git+https://github.com/<owner>/agentguard-platform.git@<tag-or-commit>
```

Use the workflow input only when you want to override the repository default for a one-off run, for example:

```text
git+https://github.com/giselleevita/agentguard-platform.git@main
```

## Expected Artifacts

The workflow uploads `agentguard-shadow-results` containing:

- `results/summary.json`
- `results/runs.json`
- `results/gate_result.json`
- `results/report_bundle/executive_summary.md`
- `results/report_bundle/manifest.json`
- `results/report_bundle/manifest.sig`

Read them in this order:

1. `executive_summary.md`
2. `gate_result.json`
3. `summary.json`
4. `runs.json`

## What Good Looks Like

For the first shadow run, the main goal is signal quality, not zero violations.

Healthy first-run outcomes:

- benign sharing and COP scenarios pass cleanly
- violations are concentrated in adversarial cases
- no obvious false positives on the benign control scenario
- the executive summary matches the intended scope of the sharing workflow

Warning signs:

- benign control scenario fails repeatedly
- all scenarios fail, which usually indicates a bad install source or a broken benchmark contract
- the workflow exits immediately in the install step because `AGENTGUARD_INSTALL_SOURCE` was not configured
- results imply blocking on tools that the scenario never intended to use

## Tuning Loop

Tune in this order:

1. Fix scenario intent if the scenario is modeling the wrong AegisAIS behavior.
2. Adjust thresholds only after at least one clean shadow run with interpretable artifacts.
3. Keep the pilot scope narrow until the sharing workflow is stable.

Threshold guidance:

- tighten `max_asr` and `max_leakage` first
- tighten `max_false_positive` only after benign controls are stable
- raise `min_task_success` only after adversarial failures are behaving as expected

## Shadow To Blocking

Do not switch a slice to blocking until all of the following are true:

- at least 3 consecutive shadow runs are stable
- benign scenarios for that slice pass consistently
- violations are limited to adversarial scenarios you intentionally model
- the install source is pinned to a known AgentGuard ref rather than an implicit moving target

When ready for a given slice:

1. pin `agentguard_install_source` to a fixed tag or commit
2. review or tighten `config/thresholds.blocking.yaml`
3. run the matching blocking workflow for that slice manually instead of editing the shadow workflow
4. keep artifact upload enabled for the first blocking runs

## Blocking Workflow

Use the blocking workflow that matches the validated slice you want to promote.

Differences from the shadow workflow:

- uses `config/thresholds.blocking.yaml`
- runs the gate in `blocking` mode
- is `workflow_dispatch` only
- uploads artifacts as a slice-specific blocking artifact bundle

Recommended use:

1. pin `AGENTGUARD_INSTALL_SOURCE` to a fixed tag or commit
2. run the blocking workflow manually
3. review `gate_result.json` and `executive_summary.md`
4. only after repeated stable blocking runs decide whether to make blocking part of normal PR enforcement

Current blocking workflow mapping:

- sharing and COP: `.github/workflows/agentguard-blocking.yml`
- export and interop review: `.github/workflows/agentguard-export-blocking.yml`
- tenant boundary and org-scope misuse: `.github/workflows/agentguard-tenant-boundary-blocking.yml`

## Stability Sweep

Use `.github/workflows/agentguard-stability-sweep.yml` to re-run the currently validated slices on a schedule or on demand.

Behavior:

- runs the sharing/COP slice and the export/interop slice in a matrix
- uses the current shadow thresholds for both slices
- uploads one artifact bundle per slice
- fails the workflow if either slice drifts beyond the current shadow thresholds

Current validated slices in the sweep:

- sharing and COP
- export and interop review
- tenant boundary and org-scope misuse

Recommended use:

1. keep the schedule enabled so drift appears before normal enforcement expands
2. use `workflow_dispatch` after meaningful AgentGuard or AegisAIS security-path changes
3. only consider broader always-on enforcement after the stability sweep stays clean over repeated runs

The shadow workflows are intentionally manual now. They no longer run on pull requests because the combined PR enforcement workflow is the single PR-time AgentGuard signal.

## PR Enforcement

Use `.github/workflows/agentguard-pr-enforcement.yml` when you want the currently validated slices to run in blocking mode on relevant pull requests.

Behavior:

- runs the sharing/COP slice and the export/interop slice in a matrix
- uses `config/thresholds.blocking.yaml`
- fails the workflow if either slice violates the current blocking thresholds
- uploads one blocking artifact bundle per slice for debugging

Current validated slices in PR enforcement:

- sharing and COP
- export and interop review
- tenant boundary and org-scope misuse

Recommended use:

1. keep this workflow scoped to the validated slices only
2. use it as the workflow-level enforcement path before changing branch protection settings
3. make it a required status check only after it stays clean under normal PR traffic

The shadow workflows should stay out of the PR path to avoid duplicate AgentGuard runs and duplicated status noise on the same change.

Current limitation:

- this repository cannot currently use GitHub branch protection or rulesets for required checks on the current private-repository plan
- the workflow still runs on pull requests and exposes pass or fail status, but GitHub cannot be configured here to hard-block merges until the plan changes or the repository becomes public

## Current Slice Status

- sharing and COP: shadow validated and manual blocking validated
- export and interop review: shadow validated and manual blocking validated
- tenant boundary and org-scope misuse: shadow validated and manual blocking validated

Both slices now have one clean manual blocking validation, but they should still stay out of broader normal PR enforcement until repeated stability sweep runs remain clean.

The repository now also has a combined PR enforcement workflow for these validated slices, but hard required-merge enforcement is blocked by the current GitHub plan on this private repository.

## Operational Notes

- the workflow explicitly enables embedded PDP fallback for this first pilot
- that keeps the shadow and blocking pilot workflows usable before a dedicated OPA policy bundle rollout
- the current pilot workflows do not start a separate OPA service container; they rely on the embedded fallback path by design
- once you want stricter production-like behavior, remove the fallback env var and require the external policy backend to answer successfully
