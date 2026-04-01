"""Lightweight contract validation for repository sample payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ContractValidationError(ValueError):
    """Raised when a sample payload violates a schema contract."""


def validate_contract_examples(*, schema_root: Path, examples_root: Path) -> None:
    pairs = {
        "Alert.schema.json": "Alert.sample.json",
        "Incident.schema.json": "Incident.sample.json",
        "Track.schema.json": "Track.sample.json",
    }
    for schema_name, example_name in pairs.items():
        schema_path = schema_root / schema_name
        example_path = examples_root / example_name
        payload = json.loads(example_path.read_text(encoding="utf-8"))
        validate_schema_instance(schema_path=schema_path, payload=payload, schema_root=schema_root)


def validate_schema_instance(*, schema_path: Path, payload: Any, schema_root: Path) -> None:
    schema = _load_json(schema_path)
    _validate_node(node=schema, value=payload, current_doc=schema, current_path=schema_path, schema_root=schema_root, breadcrumb=schema_path.name)


def _validate_node(*, node: dict[str, Any], value: Any, current_doc: dict[str, Any], current_path: Path, schema_root: Path, breadcrumb: str) -> None:
    if "$ref" in node:
        resolved_node, resolved_doc, resolved_path = _resolve_ref(node["$ref"], current_doc=current_doc, current_path=current_path, schema_root=schema_root)
        _validate_node(node=resolved_node, value=value, current_doc=resolved_doc, current_path=resolved_path, schema_root=schema_root, breadcrumb=breadcrumb)
        return

    if "const" in node and value != node["const"]:
        raise ContractValidationError(f"{breadcrumb}: expected const {node['const']!r}, got {value!r}")

    if "enum" in node and value not in node["enum"]:
        raise ContractValidationError(f"{breadcrumb}: expected one of {node['enum']!r}, got {value!r}")

    node_type = node.get("type")
    if node_type == "object":
        if not isinstance(value, dict):
            raise ContractValidationError(f"{breadcrumb}: expected object")
        required = node.get("required", [])
        for key in required:
            if key not in value:
                raise ContractValidationError(f"{breadcrumb}: missing required property {key!r}")
        properties = node.get("properties", {})
        if node.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise ContractValidationError(f"{breadcrumb}: unexpected properties {extras!r}")
        for key, child in properties.items():
            if key in value:
                _validate_node(node=child, value=value[key], current_doc=current_doc, current_path=current_path, schema_root=schema_root, breadcrumb=f"{breadcrumb}.{key}")
        return

    if node_type == "array":
        if not isinstance(value, list):
            raise ContractValidationError(f"{breadcrumb}: expected array")
        min_items = node.get("minItems")
        max_items = node.get("maxItems")
        if min_items is not None and len(value) < min_items:
            raise ContractValidationError(f"{breadcrumb}: expected at least {min_items} items")
        if max_items is not None and len(value) > max_items:
            raise ContractValidationError(f"{breadcrumb}: expected at most {max_items} items")
        item_schema = node.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                _validate_node(node=item_schema, value=item, current_doc=current_doc, current_path=current_path, schema_root=schema_root, breadcrumb=f"{breadcrumb}[{index}]")
        return

    if node_type == "string":
        if not isinstance(value, str):
            raise ContractValidationError(f"{breadcrumb}: expected string")
        return

    if node_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ContractValidationError(f"{breadcrumb}: expected number")
        minimum = node.get("minimum")
        maximum = node.get("maximum")
        if minimum is not None and value < minimum:
            raise ContractValidationError(f"{breadcrumb}: expected >= {minimum}")
        if maximum is not None and value > maximum:
            raise ContractValidationError(f"{breadcrumb}: expected <= {maximum}")
        return


def _resolve_ref(ref: str, *, current_doc: dict[str, Any], current_path: Path, schema_root: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    file_part, _, fragment = ref.partition("#")
    if file_part:
        target_path = (schema_root / file_part).resolve()
        target_doc = _load_json(target_path)
    else:
        target_path = current_path
        target_doc = current_doc

    node: Any = target_doc
    if fragment:
        for token in fragment.lstrip("/").split("/"):
            if token:
                node = node[token]
    if not isinstance(node, dict):
        raise ContractValidationError(f"Invalid ref target for {ref!r}")
    return node, target_doc, target_path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))