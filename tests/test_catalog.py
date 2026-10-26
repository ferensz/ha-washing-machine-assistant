"""Catalog integrity tests (no Home Assistant required)."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

CATALOG = Path(__file__).parents[1] / "custom_components" / "washing_machine_assistant" / "catalog.json"
CATEGORIES = {"everyday", "special", "stains", "branded", "steam", "extras"}


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.programs = {program["key"]: program for program in cls.catalog["programs"]}

    def test_program_count(self) -> None:
        self.assertEqual(self.catalog["schema_version"], 1)
        self.assertEqual(self.catalog["program_count"], 143)
        self.assertEqual(len(self.programs), 143)
        self.assertEqual(self.catalog["models"], ["RP4476BWMUC8/1-S"])

    def test_keys_and_categories(self) -> None:
        for key, program in self.programs.items():
            self.assertTrue(program["name"].strip(), key)
            self.assertIn(program["category"], CATEGORIES, key)
            self.assertIsInstance(program["parameters"], dict, key)
        counts = Counter(program["category"] for program in self.programs.values())
        self.assertEqual(
            counts,
            Counter(
                {
                    "everyday": 49,
                    "special": 40,
                    "steam": 31,
                    "stains": 9,
                    "extras": 8,
                    "branded": 6,
                }
            ),
        )

    def test_parameter_definitions(self) -> None:
        for key, program in self.programs.items():
            for param_key, spec in program["parameters"].items():
                label = f"{key}.{param_key}"
                self.assertIn(spec["type"], {"enum", "range", "bool"}, label)
                self.assertTrue(spec.get("title"), label)
                if spec["type"] == "enum":
                    values = [str(option["value"]) for option in spec["options"]]
                    self.assertTrue(values, label)
                    self.assertIn(str(spec["default"]), values, label)
                    for option in spec["options"]:
                        self.assertTrue(option["label"], label)
                elif spec["type"] == "range":
                    self.assertLessEqual(spec["min"], spec["max"], label)
                    self.assertGreater(spec["step"], 0, label)
                    value = float(spec["default"])
                    self.assertGreaterEqual(value, spec["min"], label)
                    self.assertLessEqual(value, spec["max"], label)
                    steps = (value - spec["min"]) / spec["step"]
                    self.assertAlmostEqual(steps, round(steps), places=6, msg=label)
                else:
                    self.assertIn(str(spec["default"]), {"0", "1"}, label)

    def test_parameter_types_are_consistent(self) -> None:
        expected = {
            "temp": "enum",
            "spinSpeed": "enum",
            "delayTime": "range",
            "prewash": "bool",
            "hygiene": "bool",
            "anticrease": "bool",
            "goodNight": "bool",
            "extraRinse1": "bool",
            "extraRinse2": "bool",
            "extraRinse3": "bool",
            "acquaplus": "bool",
            "dirtyLevel": "range",
            "steamLevel": "range",
            "lang": "range",
        }
        for key, program in self.programs.items():
            for param_key, spec in program["parameters"].items():
                self.assertEqual(spec["type"], expected[param_key], f"{key}.{param_key}")

    def test_labels_are_unique_after_disambiguation(self) -> None:
        used: set[str] = set()
        labels: list[str] = []
        for program in self.catalog["programs"]:
            base = program["name"].strip() or program["key"]
            label = base
            if label in used:
                label = f"{base} ({program['key']})"
            counter = 2
            while label in used:
                label = f"{base} ({program['key']} #{counter})"
                counter += 1
            used.add(label)
            labels.append(label)
        self.assertEqual(len(labels), 143)
        self.assertEqual(len(set(labels)), 143)
        self.assertTrue(any(label.startswith("Coloured (") for label in labels))
        self.assertTrue(any(label.startswith("Rinse (") for label in labels))

    def test_known_programs(self) -> None:
        cotton = self.programs["iot_wash_cotton"]
        self.assertEqual(cotton["name"], "Cotton")
        self.assertEqual(cotton["parameters"]["temp"]["default"], "60")
        self.assertEqual(cotton["parameters"]["spinSpeed"]["default"], "1400")
        self.assertEqual(cotton["parameters"]["delayTime"]["default"], "0")
        self.assertTrue(cotton["parameters"]["lang"].get("hidden"))

        checkup = self.programs["iot_checkup"]
        self.assertEqual(checkup["parameters"], {})

        easy_iron = self.programs["easy_iron"]
        self.assertEqual(easy_iron["parameters"]["steamLevel"]["type"], "range")

        self.assertEqual(
            self.programs["iot_wash_men_s_trousers"]["name"], "Men's trousers"
        )
        self.assertEqual(
            self.programs["eco_40_60_new_energy_label"]["name"], "Eco 40–60"
        )


if __name__ == "__main__":
    unittest.main()
