# Security Policy

## Supported Versions

Security fixes are applied to the latest main branch and latest tagged release.

## Reporting a Vulnerability

Do not disclose vulnerabilities publicly before coordinated remediation.

1. Report privately to maintainers with reproduction steps and impact.
2. Include affected components, commit hash/version, and proof of concept.
3. Allow time for triage and coordinated disclosure.

## Response Targets

- Initial triage: 3 business days
- Severity assessment: 5 business days
- Remediation plan: 10 business days

## Hardening Baseline

- Keep dependencies pinned and routinely updated.
- Prefer non-root containers.
- Avoid exposing databases on public interfaces.
- Use least-privilege credentials and short-lived tokens.

## BFF Identity and Access Controls

- BFF endpoints require Bearer JWT tokens and reject unsigned/invalid tokens.
- JWT verification uses issuer, audience, and JWKS controls:
  - `BFF_AUTH_ISSUER`
  - `BFF_AUTH_AUDIENCE`
  - `BFF_AUTH_JWKS_URL`
- In production, cryptographic JWT verification is mandatory.
- In development, verification can be enforced with:
  - `BFF_AUTH_ENFORCE_IN_DEV=true`

## Classification and Releasability Controls

- Sensitive BFF routes are protected with policy middleware:
  - Minimum classification (for example `CONFIDENTIAL` or `SECRET`)
  - Releasability tag requirement (default `NATO`)
- Default releasability can be overridden with:
  - `BFF_POLICY_DEFAULT_RELEASABILITY`
- Auth context includes normalized claims for downstream UI and audit workflows:
  - role
  - clearances
  - releasability
  - licenses

## Collaboration and Tenant Boundary Controls

- Sharing routes require authenticated analyst-or-higher context and derive `source_org_id` from the caller instead of a hardcoded tenant.
- The shared COP feed requires authenticated viewer-or-higher access.
- Alert status WebSocket broadcasts include `organisation_id` and are routed only to connected clients from the matching tenant.
- Alert export endpoints now enforce an explicit upper bound to avoid unbounded bulk export behavior.

## Operational Requirements

- Rotate signing keys and use short JWT TTLs.
- Emit auditable logs for denied access due to classification/releasability checks.
- Use strict least-privilege licensing claims for administrative routes.
