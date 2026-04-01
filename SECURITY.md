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