"""Catalog loading and catalog-derived mappings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .const import CATALOG_PATH, CATEGORY_LABELS, HIDDEN_PARAMETERS, PARAMETER_ORDER
from .util import ParameterValidationError, normalize_value


class CatalogError(ValueError):
    """Raised when the catalog file is missing or invalid."""


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    """Load and validate the bundled catalog."""
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise CatalogError(f"Catalog file not found: {path}") from err
    except json.JSONDecodeError as err:
        raise CatalogError(f"Catalog file is not valid JSON: {err}") from err

    errors = validate_catalog(catalog)
    if errors:
        raise CatalogError("; ".join(errors[:10]))
    return catalog


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    """Return a list of problems in a catalog document."""
    errors: list[str] = []
    if catalog.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not isinstance(catalog.get("models"), list) or not catalog["models"]:
        errors.append("models must be a non-empty list")
    programs = catalog.get("programs")
    if not isinstance(programs, list) or not programs:
        errors.append("programs must be a non-empty list")
        return errors
    if catalog.get("program_count") not in (None, len(programs)):
        errors.append("program_count does not match the programs list")

    seen: set[str] = set()
    for index, program in enumerate(programs):
        label = f"programs[{index}]"
        if not isinstance(program, dict):
            errors.append(f"{label} is not an object")
            continue
        key = program.get("key")
        if not isinstance(key, str) or not key:
            errors.append(f"{label}.key is missing")
            continue
        if key in seen:
            errors.append(f"duplicate program key {key}")
        seen.add(key)
        if not isinstance(program.get("name"), str) or not program["name"].strip():
            errors.append(f"{key}: name is missing")
        if program.get("category") not in CATEGORY_LABELS:
            errors.append(f"{key}: unknown category {program.get('category')!r}")
        parameters = program.get("parameters")
        if not isinstance(parameters, dict):
            errors.append(f"{key}: parameters must be an object")
            continue
        for param_key, spec in parameters.items():
            param_label = f"{key}.{param_key}"
            if not isinstance(spec, dict):
                errors.append(f"{param_label}: invalid spec")
                continue
            kind = spec.get("type")
            if kind not in {"enum", "range", "bool"}:
                errors.append(f"{param_label}: unknown type {kind!r}")
                continue
            if not isinstance(spec.get("title"), str) or not spec["title"]:
                errors.append(f"{param_label}: title is missing")
            if kind == "enum":
                options = spec.get("options")
                if not isinstance(options, list) or not options:
                    errors.append(f"{param_label}: enum has no options")
                    continue
                for option in options:
                    if not isinstance(option, dict) or "value" not in option or "label" not in option:
                        errors.append(f"{param_label}: invalid enum option {option!r}")
                        break
            elif kind == "range":
                for field in ("min", "max", "step"):
                    if field not in spec:
                        errors.append(f"{param_label}: range is missing {field}")
                if spec.get("step", 1) <= 0:
                    errors.append(f"{param_label}: step must be positive")
            try:
                normalize_value(spec, spec.get("default"))
            except (ParameterValidationError, KeyError) as err:
                errors.append(f"{param_label}: invalid default: {err}")
    return errors


def build_program_maps(
    programs: list[dict[str, Any]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, str],
    dict[str, str],
    list[str],
]:
    """Build key/label lookup maps and a unique label list."""
    by_key: dict[str, dict[str, Any]] = {}
    label_by_key: dict[str, str] = {}
    key_by_label: dict[str, str] = {}
    options: list[str] = []
    used: set[str] = set()

    for program in programs:
        key = str(program["key"])
        by_key[key] = program
        base = str(program.get("name") or key).strip() or key
        label = base
        if label in used:
            label = f"{base} ({key})"
        counter = 2
        while label in used:
            label = f"{base} ({key} #{counter})"
            counter += 1
        used.add(label)
        label_by_key[key] = label
        key_by_label[label] = key
        options.append(label)

    return by_key, label_by_key, key_by_label, options


def union_parameter_specs(programs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return one spec per parameter key across all programs.

    The hOn program metadata uses the same type for a given key across every
    program on this appliance. If that ever changes, fail loudly instead of
    silently mis-rendering a control.
    """
    result: dict[str, dict[str, Any]] = {}
    for program in programs:
        for key, spec in program.get("parameters", {}).items():
            if key not in result:
                result[key] = spec
                continue
            if result[key].get("type") != spec.get("type"):
                raise CatalogError(
                    f"Parameter {key!r} has conflicting types: "
                    f"{result[key].get('type')!r} and {spec.get('type')!r}"
                )
    order = {key: index for index, key in enumerate(PARAMETER_ORDER)}
    return dict(
        sorted(
            result.items(),
            key=lambda item: (order.get(item[0], len(PARAMETER_ORDER)), item[0]),
        )
    )


def ordered_parameters(program: dict[str, Any], *, include_hidden: bool = False) -> dict[str, dict[str, Any]]:
    """Return a program's parameters in UI order."""
    parameters = program.get("parameters", {})
    order = {key: index for index, key in enumerate(PARAMETER_ORDER)}
    items = sorted(
        parameters.items(),
        key=lambda item: (order.get(item[0], len(PARAMETER_ORDER)), item[0]),
    )
    if not include_hidden:
        items = [
            (key, spec)
            for key, spec in items
            if key not in HIDDEN_PARAMETERS and not spec.get("hidden")
        ]
    return dict(items)


def programs_payload(
    programs: list[dict[str, Any]], label_by_key: dict[str, str]
) -> list[dict[str, str]]:
    """Return the catalog shape the card uses for search/grouping."""
    return [
        {
            "key": program["key"],
            "name": program["name"],
            "label": label_by_key.get(program["key"], program["name"]),
            "category": program["category"],
            "category_label": CATEGORY_LABELS.get(program["category"], program["category"]),
        }
        for program in programs
    ]
