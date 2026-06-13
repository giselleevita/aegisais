#!/usr/bin/env python3
"""Fail CI on unignored high+ npm advisories outside the dev toolchain."""

from __future__ import annotations

import json
import subprocess
import sys

# Vite 8 migration is tracked separately; esbuild advisories are dev-server scoped.
DEV_TOOLCHAIN_PACKAGES = frozenset(
    {"esbuild", "vite", "tsx", "@vitejs/plugin-react"}
)


def main() -> int:
    proc = subprocess.run(
        ["npm", "audit", "--audit-level=high", "--json"],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        print(proc.stdout or proc.stderr, file=sys.stderr)
        return proc.returncode or 1

    unhandled: list[tuple[str, str]] = []
    for name, vuln in data.get("vulnerabilities", {}).items():
        severity = vuln.get("severity")
        if severity not in {"high", "critical"}:
            continue
        if name in DEV_TOOLCHAIN_PACKAGES:
            continue
        unhandled.append((name, severity))

    if unhandled:
        print("Unhandled high/critical npm vulnerabilities:", file=sys.stderr)
        for name, severity in unhandled:
            print(f"  - {name} ({severity})", file=sys.stderr)
        return 1

    if proc.returncode not in (0, None):
        print(
            "Only dev-toolchain advisories remain (esbuild/vite); "
            "vite 8 migration tracked separately."
        )
    else:
        print("No high/critical npm vulnerabilities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
