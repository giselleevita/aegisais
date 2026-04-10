---
name: Six-Phase Audit Review
description: "Run a six-phase read-only audit and produce a prioritized implementation plan without making code changes. Use when reviewing a codebase, module, API surface, or feature slice for engineering and product risks before any edits are made."
argument-hint: "What repo, folder, module, API, or file set should be audited in read-only mode?"
agent: agent
---

Run a focused six-phase audit for the specified target in strict read-only mode. Produce a concrete implementation plan, but do not edit files or execute write operations.

Target:

- Use the user argument as the primary audit scope.
- If no explicit target is provided, use the current workspace or the currently relevant code area from chat context.
- Prefer code and tests over documentation claims when they conflict.

Audit phases:

1. Schema

- Find structure defects, missing constraints, incorrect nullability, wrong field types, weak enums, bad defaults, and missing indexes.
- Check whether persistence models match the implied domain rules.
- Flag places where data integrity depends on application code instead of schema enforcement.

2. Routes

- Find auth gaps, missing authorization checks, weak input validation, inconsistent response contracts, wrong or misleading status codes, and unsafe export/download paths.
- Check whether routes are backed by persisted and authorized entities rather than caller-supplied trust.

3. Business Logic

- Find transaction boundary issues, race conditions, duplicate creation risks, side effects without rollback, non-idempotent handlers, and hidden coupling.
- Check retry behavior, concurrency assumptions, and whether state transitions are explicit and safe.

4. Security

- Find privilege-escalation paths, injection risks, tenant-isolation gaps, weak secrets handling, unsafe CORS behavior, missing audit coverage, and unsafe trust boundaries.
- Prioritize logic-layer security weaknesses over generic checklist items.

5. Performance

- Find N+1 queries, missing pagination, heavy list endpoints, repeated polling inefficiencies, expensive joins, unbounded exports, and redundant client refresh loops.
- Call out hotspots likely to fail first at scale.

6. Structure

- Find layer violations, God objects, duplicated logic, misplaced responsibilities, weak module boundaries, and architecture drift.
- Check whether the current structure supports safe future change or amplifies regression risk.

Method:

- Build findings from actual code paths, not generic best practices.
- Read enough surrounding code to understand each issue at root-cause level.
- Distinguish clearly between:
  - implemented and verified
  - partially implemented
  - documented but not implemented
  - broken or risky
- If tests or lint are available, use them when useful to confirm impact.
- Ignore unrelated issues unless they materially affect the audited flow.
- Prefer root-cause analysis over symptom lists.
- Stay in read-only mode throughout the task.

Output format:

## Executive Summary

- 3 bullets: biggest risk, biggest opportunity, top action

## Findings

- Group by the 6 phases above
- For each finding include:
  - Title
  - Severity: Critical / High / Medium / Low
  - Why it matters
  - Evidence: concrete file references and behavior
  - Recommended fix

## User Flow Impact

- Explain which user flows or operator workflows are broken, degraded, or not covered
- Call out missing use cases and mismatches between intended flow and actual implementation

## Validation Status

- State what was verified via code reading, tests, lint, or runtime checks
- State what could not be verified

## Prioritized Action Plan

- Split into:
  - Immediate fixes
  - Next sprint fixes
  - Structural follow-up

## Implementation Plan

- Identify which findings should be implemented first
- Group related fixes into coherent batches
- For each batch, state expected impact, likely files, and validation steps
- Do not implement the changes in this prompt

Execution rules:

- Do not modify files, create files, or run write operations.
- If a fix is obvious, describe it precisely in the plan instead of applying it.
- If a finding needs clarification, external credentials, production access, or high-risk product decisions, leave it in the plan and state the blocker.
- End with the best next implementation batch for a follow-up execution prompt.

Quality bar:

- Be specific, technical, and unsentimental.
- Prefer high-signal findings over exhaustive noise.
- Do not stop at symptoms; explain the root cause.
- If documentation conflicts with code, say so explicitly.
- If no major issues are found in a phase, say that directly and note residual risk.
- Do not dilute the report with generic advice.
