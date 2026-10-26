"""Pure helpers for validating and applying washing-machine parameters."""

from __future__ import annotations

from typing import Any


class ParameterValidationError(ValueError):
    """Raised when a parameter value is not valid for a program."""


def _as_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError) as err:
        raise ParameterValidationError(f"Expected a number, got {value!r}") from err


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def enum_label_map(spec: dict[str, Any]) -> dict[str, str]:
    """Return label -> value for an enum parameter."""
    return {str(option["label"]): str(option["value"]) for option in spec.get("options", [])}


def enum_value_map(spec: dict[str, Any]) -> dict[str, str]:
    """Return value -> label for an enum parameter."""
    return {str(option["value"]): str(option["label"]) for option in spec.get("options", [])}


def normalize_value(spec: dict[str, Any], value: Any) -> str:
    """Validate a value against a parameter spec and return its canonical string.

    Enum parameters accept either the stored value or its display label. This
    makes service calls friendlier (``"60 °C"`` as well as ``"60"``).
    """
    kind = spec.get("type")
    if kind == "enum":
        allowed = {str(option["value"]) for option in spec.get("options", [])}
        raw = str(value)
        if raw in allowed:
            return raw
        label_map = enum_label_map(spec)
        if raw in label_map:
            return label_map[raw]
        raise ParameterValidationError(
            f"Value {value!r} is not one of {sorted(allowed)}"
        )

    if kind == "range":
        number = _as_float(value)
        minimum = _as_float(spec["min"])
        maximum = _as_float(spec["max"])
        step = _as_float(spec.get("step", 1))
        if number < minimum or number > maximum:
            raise ParameterValidationError(
                f"Value {number:g} is outside {minimum:g}..{maximum:g}"
            )
        if step > 0:
            steps = (number - minimum) / step
            if abs(steps - round(steps)) > 1e-6:
                raise ParameterValidationError(
                    f"Value {number:g} is not on a {step:g} step from {minimum:g}"
                )
        return _format_number(number)

    if kind == "bool":
        if isinstance(value, bool):
            return "1" if value else "0"
        raw = str(value).strip().lower()
        if raw in {"1", "true", "on", "yes"}:
            return "1"
        if raw in {"0", "false", "off", "no"}:
            return "0"
        raise ParameterValidationError(f"Expected a boolean, got {value!r}")

    raise ParameterValidationError(f"Unknown parameter type {kind!r}")


def default_value(spec: dict[str, Any]) -> str:
    """Return the canonical default value for a parameter."""
    try:
        return normalize_value(spec, spec.get("default", "0"))
    except ParameterValidationError:
        if spec.get("type") == "enum" and spec.get("options"):
            return str(spec["options"][0]["value"])
        if spec.get("type") == "range":
            return _format_number(_as_float(spec.get("min", 0)))
        return "0"


def defaults_for(program: dict[str, Any]) -> dict[str, str]:
    """Return every parameter for a program set to its default."""
    return {
        key: default_value(spec)
        for key, spec in program.get("parameters", {}).items()
    }


def coerce_params(
    program: dict[str, Any],
    values: dict[str, Any] | None,
    *,
    strict: bool = True,
) -> dict[str, str]:
    """Merge values into a program's defaults.

    Unknown keys are ignored. With ``strict=True`` an invalid supplied value
    raises; with ``strict=False`` it falls back to the default (useful for
    favorites saved against an older catalog).
    """
    result = defaults_for(program)
    if not values:
        return result
    for key, spec in program.get("parameters", {}).items():
        if key not in values:
            continue
        try:
            result[key] = normalize_value(spec, values[key])
        except ParameterValidationError:
            if strict:
                raise
    return result


def parameter_display_value(spec: dict[str, Any], value: Any) -> str:
    """Return a human-readable value for a parameter."""
    kind = spec.get("type")
    if kind == "enum":
        return enum_value_map(spec).get(str(value), str(value))
    if kind == "bool":
        return "On" if str(value) == "1" else "Off"
    if kind == "range":
        unit = spec.get("unit")
        return f"{value} {unit}".strip()
    return str(value)


def parameter_summary(program: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """Build a compact summary used by the card and by dry-run responses."""
    parameters = program.get("parameters", {})
    summary: dict[str, Any] = {
        "program": program.get("name"),
        "program_key": program.get("key"),
    }
    for key in ("temp", "spinSpeed", "delayTime"):
        spec = parameters.get(key)
        if spec and key in values:
            summary[key] = parameter_display_value(spec, values[key])
    enabled = []
    for key, spec in parameters.items():
        if spec.get("type") == "bool" and str(values.get(key)) == "1":
            enabled.append(spec.get("title", key))
    if enabled:
        summary["options"] = enabled
    return summary
