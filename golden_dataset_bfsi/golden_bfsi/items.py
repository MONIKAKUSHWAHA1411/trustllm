"""Load golden items and validate their shape against the JSON schema.

The validator is a small stdlib-only checker that covers the subset of
JSON Schema this dataset uses: ``type``, ``enum``, ``pattern``, ``required``
and nested object ``properties`` with ``additionalProperties: false``. It is
deliberately not a general JSON Schema engine — it exists so the invariant
tests have zero third-party dependencies.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .paths import L0_DATA, SCHEMA

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "boolean": bool,
}


def load_items(path=L0_DATA) -> List[Dict[str, Any]]:
    """Read a JSONL file, skipping blank lines and ``//`` comment lines."""
    items: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ValueError(f"{path}:{lineno}: invalid JSON ({exc})") from exc
    return items


def load_schema(path=SCHEMA) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _check(schema: dict, value: Any, where: str, errors: List[str]) -> None:
    expected = schema.get("type")
    if expected:
        py_type = _JSON_TYPES[expected]
        # bool is a subclass of int, so a boolean must not satisfy "number".
        if expected == "number" and isinstance(value, bool):
            errors.append(f"{where}: expected number, got boolean")
            return
        if not isinstance(value, py_type):
            errors.append(f"{where}: expected {expected}, got {type(value).__name__}")
            return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} not in {schema['enum']}")

    if "pattern" in schema and isinstance(value, str):
        if not re.match(schema["pattern"], value):
            errors.append(f"{where}: {value!r} does not match /{schema['pattern']}/")

    if expected == "object":
        _check_object(schema, value, where, errors)
    elif expected == "array" and "items" in schema:
        for i, element in enumerate(value):
            _check(schema["items"], element, f"{where}[{i}]", errors)


def _check_object(schema: dict, value: dict, where: str, errors: List[str]) -> None:
    props = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in value:
            errors.append(f"{where}: missing required field '{key}'")
    if schema.get("additionalProperties") is False:
        for key in value:
            if key not in props:
                errors.append(f"{where}: unexpected field '{key}'")
    for key, subschema in props.items():
        if key in value:
            prefix = f"{where}.{key}" if where else key
            _check(subschema, value[key], prefix, errors)


def validate_item(item: Dict[str, Any], schema: dict | None = None) -> List[str]:
    """Return a list of human-readable schema errors ([] means valid)."""
    schema = schema or load_schema()
    errors: List[str] = []
    _check(schema, item, item.get("id", "<item>"), errors)
    return errors
