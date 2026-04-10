# AgentGuard Production Go-Live Checklist

Use this checklist before treating AgentGuard as a production enforcement control in AegisAIS.

## Release Source

- `AGENTGUARD_INSTALL_SOURCE` is pinned to a tagged AgentGuard release, not `main`
- the pinned release has published release notes and a retained rollback target
- the install source used in the last validation run matches the documented release pin

## Policy Backend

- the production path uses a reachable external OPA backend
- `AGENTGUARD_ALLOW_EMBEDDED_PDP_FALLBACK` is disabled for the production validation path
- the OPA policy bundle comes from the same AgentGuard release being approved

## Validation Evidence

- the latest `agentguard-production-validation.yml` run passed for all validated slices
- the latest `agentguard-stability-sweep.yml` run passed for all validated slices
- the latest `agentguard-pr-enforcement.yml` run passed for all validated slices
- report bundles and OPA logs from the production validation run are retained

## Operational Readiness

- owners for AgentGuard failures are named for engineering and security response
- thresholds in `.agentguard/config/thresholds.blocking.yaml` match the approved enforcement posture
- rollback instructions are available and tested against the previous tagged AgentGuard release
- the current GitHub plan limitation on required checks is understood by the operators

## Go / No-Go Rule

Do not treat AgentGuard as a production enforcement control if any validated slice has not passed the external-OPA production workflow on the same tagged release that is pinned in repository configuration.