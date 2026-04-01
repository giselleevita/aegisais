from pathlib import Path

import pytest

from app.modules.integrations.contracts_validator import (
    ContractValidationError,
    validate_contract_examples,
    validate_schema_instance,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_contract_examples_validate_against_schemas():
    repo_root = _repo_root()
    validate_contract_examples(
        schema_root=repo_root / "packages/contracts/schemas",
        examples_root=repo_root / "packages/contracts/examples",
    )


def test_alert_schema_rejects_missing_required_field():
    repo_root = _repo_root()
    payload = {
        "id": "alert-1",
        "alertType": "teleport",
        "status": "new",
        "createdAt": "2026-03-31T12:00:00Z",
        "priority": "p2",
        "message": "Missing confidence should fail",
        "provenance": {
            "source": "ais",
            "processor": "detector",
            "ingestedAt": "2026-03-31T11:59:00Z",
        },
        "access": {
            "classification": "restricted",
            "allowedRoles": ["analyst"],
        },
    }
    with pytest.raises(ContractValidationError):
        validate_schema_instance(
            schema_path=repo_root / "packages/contracts/schemas/Alert.schema.json",
            payload=payload,
            schema_root=repo_root / "packages/contracts/schemas",
        )