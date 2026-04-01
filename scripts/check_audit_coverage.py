#!/usr/bin/env python3
"""Fail CI when audit-sensitive changes land without audit evidence updates."""

from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
from pathlib import Path


PROTECTED_PATTERNS = (
    "apps/api/app/api/v1/incidents.py",
    "apps/api/app/api/v1/vessels.py",
    "apps/api/app/modules/incidents/*",
    "apps/api/app/modules/auth/service.py",
    "apps/api/app/services/workers/alert_worker.py",
    "apps/api/app/modules/alerts/models.py",
    "apps/api/app/modules/billing/*",  # BL-010 usage ledger
)

EVIDENCE_PATTERNS = (
    "docs/AUDIT_COVERAGE_MATRIX.md",
    "docs/SECURITY_EVIDENCE_PACK.md",              # BL-014
    "docs/security/SECURITY_AND_COMPLIANCE.md",    # BL-014
    "docs/INTEROPERABILITY_PROFILE.md",            # BL-015
    "docs/SUPPLY_CHAIN_ASSURANCE.md",              # BL-016
    "docs/FUNDING_PILOT_EVIDENCE_TEMPLATE.md",     # BL-017
    "docs/CONSORTIUM_EXECUTION_MODEL.md",          # BL-018
    "packages/contracts/schemas/ImportBundle.schema.json",  # BL-015
    "apps/api/app/modules/audit/*",
    "apps/api/tests/*audit*",
    "apps/api/tests/test_incidents_api.py",
    "apps/api/tests/test_alerts_vessels_api.py",
    "apps/api/tests/test_org_scope.py",
    "apps/api/tests/test_alert_worker_audit.py",
    "apps/api/tests/test_alert_idempotency.py",
    "apps/api/tests/test_alert_evidence_hash.py",  # BL-009
    "apps/api/tests/test_billing_usage_ledger.py", # BL-010
    "apps/api/tests/test_competitor_import.py",    # BL-011
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _changed_files() -> list[str]:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    base_ref = os.environ.get("GITHUB_BASE_REF", "")

    if event_name == "pull_request" and base_ref:
        try:
            subprocess.check_call(["git", "fetch", "origin", base_ref, "--depth=1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            pass
        merge_base = _git("merge-base", "HEAD", f"origin/{base_ref}")
        diff_range = f"{merge_base}..HEAD"
    else:
        try:
            _git("rev-parse", "HEAD~1")
            diff_range = "HEAD~1..HEAD"
        except subprocess.CalledProcessError:
            return []

    out = _git("diff", "--name-only", diff_range)
    return [line for line in out.splitlines() if line]


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    changed = _changed_files()
    if not changed:
        print("No diff scope detected for audit coverage gate; skipping.")
        return 0

    protected = [path for path in changed if _matches_any(path, PROTECTED_PATTERNS)]
    evidence = [path for path in changed if _matches_any(path, EVIDENCE_PATTERNS)]

    if protected and not evidence:
        print("Audit coverage gate failed.")
        print("Protected files changed without audit evidence updates:")
        for path in protected:
            print(f" - {path}")
        print("Expected at least one matching evidence update, such as:")
        for pattern in EVIDENCE_PATTERNS:
            print(f" - {pattern}")
        return 1

    print("Audit coverage gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())