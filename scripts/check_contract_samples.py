#!/usr/bin/env python3
"""Validate contract example payloads against repository JSON schemas."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "apps/api"))

    from app.modules.integrations.contracts_validator import validate_contract_examples

    validate_contract_examples(
        schema_root=repo_root / "packages/contracts/schemas",
        examples_root=repo_root / "packages/contracts/examples",
    )
    print("Contract sample validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())