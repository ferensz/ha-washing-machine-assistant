"""Tests for the pure parameter helpers."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

UTIL_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "washing_machine_assistant"
    / "util.py"
)
spec = importlib.util.spec_from_file_location("washing_machine_util", UTIL_PATH)
assert spec and spec.loader
util = importlib.util.module_from_spec(spec)
spec.loader.exec_module(util)


PROGRAM = {
    "key": "test",
    "name": "Test",
    "parameters": {
        "temp": {
            "type": "enum",
            "title": "Temperature",
            "options": [
                {"value": "0", "label": "Cold"},
                {"value": "40", "label": "40 °C"},
                {"value": "60", "label": "60 °C"},
            ],
            "default": "40",
        },
        "spinSpeed": {
            "type": "enum",
            "title": "Spin speed",
            "options": [
                {"value": "0", "label": "No spin"},
                {"value": "800", "label": "800 rpm"},
            ],
            "default": "800",
        },
        "delayTime": {
            "type": "range",
            "title": "Delay time",
            "min": 0,
            "max": 120,
            "step": 30,
            "default": "0",
            "unit": "min",
        },
        "prewash": {"type": "bool", "title": "Prewash", "default": "0"},
    },
}


class UtilTests(unittest.TestCase):
    def test_enum_accepts_value_and_label(self) -> None:
        spec = PROGRAM["parameters"]["temp"]
        self.assertEqual(util.normalize_value(spec, "60"), "60")
        self.assertEqual(util.normalize_value(spec, "60 °C"), "60")
        self.assertEqual(util.normalize_value(spec, 40), "40")
        with self.assertRaises(util.ParameterValidationError):
            util.normalize_value(spec, "90")

    def test_range_step_and_bounds(self) -> None:
        spec = PROGRAM["parameters"]["delayTime"]
        self.assertEqual(util.normalize_value(spec, "60"), "60")
        self.assertEqual(util.normalize_value(spec, 30.0), "30")
        with self.assertRaises(util.ParameterValidationError):
            util.normalize_value(spec, 45)
        with self.assertRaises(util.ParameterValidationError):
            util.normalize_value(spec, 150)

    def test_bool(self) -> None:
        spec = PROGRAM["parameters"]["prewash"]
        self.assertEqual(util.normalize_value(spec, True), "1")
        self.assertEqual(util.normalize_value(spec, "off"), "0")
        with self.assertRaises(util.ParameterValidationError):
            util.normalize_value(spec, "maybe")

    def test_defaults_and_coercion(self) -> None:
        defaults = util.defaults_for(PROGRAM)
        self.assertEqual(
            defaults,
            {
                "temp": "40",
                "spinSpeed": "800",
                "delayTime": "0",
                "prewash": "0",
            },
        )
        merged = util.coerce_params(
            PROGRAM, {"temp": "60", "prewash": True, "unknown": "x"}
        )
        self.assertEqual(merged["temp"], "60")
        self.assertEqual(merged["prewash"], "1")
        self.assertNotIn("unknown", merged)

    def test_non_strict_falls_back_on_invalid_values(self) -> None:
        merged = util.coerce_params(PROGRAM, {"temp": "90"}, strict=False)
        self.assertEqual(merged["temp"], "40")
        with self.assertRaises(util.ParameterValidationError):
            util.coerce_params(PROGRAM, {"temp": "90"}, strict=True)

    def test_summary(self) -> None:
        summary = util.parameter_summary(
            PROGRAM,
            {"temp": "60", "spinSpeed": "800", "delayTime": "30", "prewash": "1"},
        )
        self.assertEqual(summary["program"], "Test")
        self.assertEqual(summary["temp"], "60 °C")
        self.assertEqual(summary["spinSpeed"], "800 rpm")
        self.assertEqual(summary["delayTime"], "30 min")
        self.assertEqual(summary["options"], ["Prewash"])


if __name__ == "__main__":
    unittest.main()
