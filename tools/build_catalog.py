#!/usr/bin/env python3
"""Build the washing-machine program catalog from hOn program notifications.

Usage:
    python tools/build_catalog.py notifications.json custom_components/washing_machine_assistant/catalog.json

The input is the JSON returned by the ha-mcp ha_get_overview tool with
include_notifications=True, or any JSON object with a top-level "notifications"
list. Each notification title must look like "Program [iot_wash_cotton]".

Nothing in this script talks to Home Assistant; it only transforms the dump.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MODEL = "RP4476BWMUC8/1-S"
BRAND = "Candy"
APPLIANCE_TYPES = ["WM"]

CATEGORY_ORDER = ["everyday", "special", "stains", "branded", "steam", "extras"]

PARAM_ORDER = [
    "temp",
    "spinSpeed",
    "delayTime",
    "prewash",
    "hygiene",
    "anticrease",
    "goodNight",
    "extraRinse1",
    "extraRinse2",
    "extraRinse3",
    "acquaplus",
    "dirtyLevel",
    "steamLevel",
    "lang",
]

PARAM_META = {
    "temp": {"title": "Temperature", "icon": "mdi:thermometer"},
    "spinSpeed": {"title": "Spin speed", "icon": "mdi:rotate-right"},
    "delayTime": {"title": "Delay time", "icon": "mdi:timer-plus", "unit": "min"},
    "prewash": {"title": "Prewash", "icon": "mdi:water"},
    "hygiene": {"title": "Hygiene", "icon": "mdi:shield-check"},
    "anticrease": {"title": "Anti-crease", "icon": "mdi:iron"},
    "goodNight": {"title": "Good night", "icon": "mdi:weather-night"},
    "extraRinse1": {"title": "Extra rinse 1", "icon": "mdi:water-plus"},
    "extraRinse2": {"title": "Extra rinse 2", "icon": "mdi:water-plus"},
    "extraRinse3": {"title": "Extra rinse 3", "icon": "mdi:water-plus"},
    "acquaplus": {"title": "Aqua plus", "icon": "mdi:water-plus-outline"},
    "dirtyLevel": {"title": "Soiling level", "icon": "mdi:water-percent"},
    "steamLevel": {"title": "Steam level", "icon": "mdi:weather-fog"},
    "lang": {"title": "Language", "icon": "mdi:translate", "hidden": True},
}

NAME_OVERRIDES = {
    "iot_wash_masks_refresh": "Masks refresh",
    "iot_wash_masks_sanification": "Masks sanitisation",
    "iot_wash_masks_sanification_steam": "Masks sanitisation steam",
    "iot_wash_men_s_trousers": "Men's trousers",
    "iot_wash_swimsuits_and_bikinis": "Swimsuits & bikinis",
    "iot_wash_pets_odours_stains_removal": "Pets: odours & stains",
    "iot_wash_pets_hair_removal": "Pets: hair removal",
    "iot_wash_pets": "Pets",
    "iot_wash_pets_steam": "Pets steam",
    "iot_wash_delicate_antiallergy": "Delicate anti-allergy",
    "iot_wash_delicate_antiallergy_steam": "Delicate anti-allergy steam",
    "iot_wash_colored_anti_stain": "Coloured anti-stain",
    "iot_wash_stains_remover": "Stains remover",
    "iot_wash_sport_anti_odor": "Sport anti-odour",
    "iot_wash_anti_mites": "Anti-mites",
    "iot_wash_quick_drum_cleaner": "Quick drum cleaner",
    "iot_wash_perfect_white": "Perfect white",
    "iot_wash_perfect_white_steam": "Perfect white steam",
    "iot_wash_blood_stains": "Blood stains",
    "iot_wash_fruit_stains": "Fruit stains",
    "iot_wash_wine_stains": "Wine stains",
    "iot_wash_chocolate_stains": "Chocolate stains",
    "iot_wash_refresh_14_min": "Refresh 14 min",
    "iot_wash_denim_jeans": "Denim jeans",
    "iot_wash_gym_fit": "Gym fit",
    "iot_wash_down_jackets": "Down jackets",
    "iot_wash_diving_suits": "Diving suits",
    "iot_wash_coloured_curtains": "Coloured curtains",
    "iot_wash_curtains": "Curtains",
    "iot_wash_curtains_steam": "Curtains steam",
    "iot_wash_cuddly_toys": "Cuddly toys",
    "iot_wash_coloured_bed_linen": "Coloured bed linen",
    "iot_wash_coloured_bed_linen_steam": "Coloured bed linen steam",
    "iot_wash_bed_linen": "Bed linen",
    "iot_wash_bed_linen_steam": "Bed linen steam",
    "iot_wash_bathrobe": "Bathrobe",
    "iot_wash_bathrobe_steam": "Bathrobe steam",
    "iot_wash_backpacks": "Backpacks",
    "iot_wash_playsuits": "Playsuits",
    "iot_wash_playsuits_steam": "Playsuits steam",
    "iot_wash_baby_sanitizer": "Baby sanitizer",
    "iot_wash_baby_sanitizer_steam": "Baby sanitizer steam",
    "iot_wash_technical_jackets": "Technical jackets",
    "iot_wash_technical_fabrics": "Technical fabrics",
    "iot_wash_tablecloths": "Tablecloths",
    "iot_wash_tablecloths_steam": "Tablecloths steam",
    "iot_wash_coloured_shirts": "Coloured shirts",
    "iot_wash_coloured_shirts_steam": "Coloured shirts steam",
    "iot_wash_shirts": "Shirts",
    "iot_wash_shirts_steam": "Shirts steam",
    "iot_wash_lingerie": "Lingerie",
    "iot_wash_new_clothes": "New clothes",
    "iot_wash_ski_suit": "Ski suit",
    "iot_wash_silk": "Silk",
    "iot_wash_trainers": "Trainers",
    "iot_wash_mats": "Mats",
    "iot_wash_cashmere": "Cashmere",
    "iot_wash_delicate_colors": "Delicate colours",
    "iot_wash_delicate_colors_steam": "Delicate colours steam",
    "iot_wash_delicate_tablecloths": "Delicate tablecloths",
    "iot_wash_delicate_tablecloths_steam": "Delicate tablecloths steam",
    "iot_wash_delicate": "Delicate",
    "iot_wash_delicate_steam": "Delicate steam",
    "iot_wash_delicate_dark": "Delicate dark",
    "iot_wash_delicate_whites": "Delicate whites",
    "iot_wash_colored_delicate": "Coloured delicate",
    "iot_wash_coloured": "Coloured",
    "iot_wash_coloured_steam": "Coloured steam",
    "iot_wash_colored": "Coloured",
    "iot_wash_whites": "Whites",
    "iot_wash_whites_44": "Whites 44",
    "iot_wash_whites_59": "Whites 59",
    "iot_wash_whites_xl": "Whites XL",
    "iot_wash_dark": "Dark colours",
    "iot_wash_dark_steam": "Dark colours steam",
    "iot_wash_darks_and_coloured_44": "Darks & coloured 44",
    "iot_wash_darks_and_coloured_59": "Darks & coloured 59",
    "iot_wash_darks_and_coloured_xl": "Darks & coloured XL",
    "iot_wash_mix_and_coloured_44": "Mix & coloured 44",
    "iot_wash_mix_and_coloured_59": "Mix & coloured 59",
    "iot_wash_mix_and_coloured_xl": "Mix & coloured XL",
    "iot_wash_super_saving": "Super saving",
    "iot_wash_cold_wash": "Cold wash",
    "iot_wash_handwash": "Handwash",
    "iot_wash_handwash_colored": "Handwash coloured",
    "iot_wash_handwash_dark": "Handwash dark",
    "iot_wash_resistant_colored": "Resistant coloured",
    "iot_wash_resistant_dark": "Resistant dark",
    "iot_wash_resistant_whites": "Resistant whites",
    "iot_wash_resistant_cotton_steam": "Resistant cotton steam",
    "iot_wash_synthetic_and_coloured_steam": "Synthetic & coloured steam",
    "iot_wash_cotton": "Cotton",
    "iot_wash_cotton_steam": "Cotton steam",
    "iot_wash_synthetic": "Synthetics",
    "iot_wash_synthetic_steam": "Synthetics steam",
    "iot_wash_mixed": "Mixed",
    "iot_wash_mixed_steam": "Mixed steam",
    "iot_wash_wool": "Wool",
    "iot_wash_rapid_14": "Rapid 14 min",
    "iot_wash_rapid_30": "Rapid 30 min",
    "iot_wash_rapid_44": "Rapid 44 min",
    "iot_wash_rapid_59": "Rapid 59 min",
    "iot_wash_rapid_59_steam": "Rapid 59 min steam",
    "iot_wash_sport": "Sport",
    "iot_wash_spin": "Spin",
    "iot_wash_rinse": "Rinse",
    "iot_wash_100_custom_wash": "Custom wash 100",
    "iot_wash_100_custom_wash_steam": "Custom wash 100 steam",
    "eco_40_60_new_energy_label": "Eco 40–60",
    "20_degrees_new_energy_label": "20 °C",
    "delicati_59": "Delicate 59 min",
    "iot_delicati_59_steam": "Delicate 59 min steam",
    "iot_intensive_40_steam": "Intensive 40 steam",
    "iot_special_39_full_load_steam": "Special 39 full load steam",
    "iot_perfect_cotton_59_steam": "Perfect cotton 59 min steam",
    "iot_mix_and_colour_59_steam": "Mix & colour 59 min steam",
    "iot_wash_dash_clean_cycle": "Dash clean cycle",
    "iot_wash_dash_fresh_cycle": "Dash fresh cycle",
    "iot_wash_dash_cold_cycle": "Dash cold cycle",
    "iot_wash_ariel_clean_cycle": "Ariel clean cycle",
    "iot_wash_ariel_fresh_cycle": "Ariel fresh cycle",
    "iot_wash_ariel_cold_cycle": "Ariel cold cycle",
    "night_wash": "Night wash",
    "handwash_wool": "Handwash / wool",
    "drain_spin": "Drain & spin",
    "steam_hygiene_plus": "Steam Hygiene+",
}


def humanize(key: str) -> str:
    if key in NAME_OVERRIDES:
        return NAME_OVERRIDES[key]
    name = key
    if name.startswith("iot_wash_"):
        name = name[len("iot_wash_") :]
    elif name.startswith("iot_"):
        name = name[len("iot_") :]
    name = re.sub(r"_(\d+)_min$", r" \1 min", name)
    name = re.sub(r"_(\d+)$", r" \1", name)
    name = re.sub(r"_xl$", " XL", name)
    name = name.replace("_", " ")
    name = re.sub(r"\band\b", "&", name, flags=re.IGNORECASE)
    name = re.sub(r"\b\w", lambda m: m.group(0).upper(), name)
    name = re.sub(r"\bSteam\b", "steam", name)
    name = re.sub(r"\bMin\b", "min", name)
    return name


def category(key: str) -> str:
    if re.search(r"ariel|dash", key):
        return "branded"
    if "steam" in key:
        return "steam"
    if re.search(r"stain|blood|wine|chocolate|fruit|anti_mites|bleaching", key):
        return "stains"
    if re.search(
        r"checkup|tumbling|autoclean|^rinse$|^drain_spin$|iot_wash_rinse|iot_wash_spin|quick_drum_cleaner",
        key,
    ):
        return "extras"
    if re.search(
        r"mask|technical|tablecloth|swimsuit|ski|silk|shirt|trouser|trainer|mats|lingerie|new_clothes|pets|sport|denim|gym|down|diving|curtain|cuddly|cashmere|bed_linen|bathrobe|backpack|playsuit|baby|delicate",
        key,
    ):
        return "special"
    return "everyday"


def parse_default(raw: str) -> str:
    raw = raw.strip()
    if raw.lower() in {"none", "null"}:
        return "0"
    return raw


def parse_parameter_line(line: str) -> tuple[str, dict] | None:
    if ":" not in line:
        return None
    key, rest = line.split(":", 1)
    key = key.strip()
    rest = rest.strip()
    if not rest.startswith("["):
        return None
    close = rest.find("]")
    if close < 0:
        return None
    inside = rest[1:close].strip()
    tail = rest[close + 1 :]
    default_match = re.search(r"Default:\s*([^\s]+)", tail)
    step_match = re.search(r"Step:\s*([^\s]+)", tail)
    default = parse_default(default_match.group(1)) if default_match else "0"
    meta = PARAM_META.get(key, {})
    param: dict = {
        "title": meta.get("title", humanize(key)),
        "icon": meta.get("icon", "mdi:tune"),
    }

    values = [v.strip() for v in inside.split(",")]
    if len(values) > 1:
        # Enum values can contain spaces / units? They are plain values here.
        options = []
        for value in values:
            label = value
            if key == "temp":
                label = "Cold" if value == "0" else f"{value} °C"
            elif key == "spinSpeed":
                label = "No spin" if value == "0" else f"{value} rpm"
            options.append({"value": value, "label": label})
        allowed = {opt["value"] for opt in options}
        if default not in allowed:
            default = options[0]["value"]
        param.update({"type": "enum", "options": options, "default": default})
    else:
        bounds = [v.strip() for v in inside.split("-")]
        if len(bounds) != 2:
            return None
        try:
            minimum = int(bounds[0])
            maximum = int(bounds[1])
        except ValueError:
            try:
                minimum = float(bounds[0].replace(",", "."))
                maximum = float(bounds[1].replace(",", "."))
            except ValueError:
                return None
        step = 1
        if step_match:
            try:
                step = int(step_match.group(1))
            except ValueError:
                step = 1
        if minimum == 0 and maximum == 1 and step == 1:
            if default not in {"0", "1"}:
                default = "0"
            param.update({"type": "bool", "default": default})
        else:
            param.update(
                {
                    "type": "range",
                    "min": minimum,
                    "max": maximum,
                    "step": step,
                    "default": default,
                }
            )
            if meta.get("unit"):
                param["unit"] = meta["unit"]
    if meta.get("hidden"):
        param["hidden"] = True
    return key, param


def parse_notification(notification: dict) -> dict | None:
    title = notification.get("title", "")
    match = re.match(r"^Program \[(.+)\]$", title)
    if not match:
        return None
    key = match.group(1).strip()
    message = notification.get("message", "")
    if "#### Parameters:" not in message:
        return None
    block = message.split("#### Parameters:", 1)[1]
    block = block.split("#### Start this program", 1)[0]
    lines = [line.strip() for line in block.splitlines() if line.strip()]

    params: dict[str, dict] = {}
    for line in lines:
        parsed = parse_parameter_line(line)
        if parsed:
            param_key, param = parsed
            params[param_key] = param

    # Put parameters in a stable, UI-friendly order. Unknown keys go at the end.
    ordered: dict[str, dict] = {}
    for param_key in PARAM_ORDER:
        if param_key in params:
            ordered[param_key] = params[param_key]
    for param_key, param in params.items():
        if param_key not in ordered:
            ordered[param_key] = param

    # Sanity check against the ready-to-use default parameters in the message.
    default_params: dict = {}
    default_match = re.search(r"parameters:\s*>-\s*\n\s*(\{[^\n]*\})", message)
    if default_match:
        try:
            default_params = ast.literal_eval(default_match.group(1))
        except (ValueError, SyntaxError):
            default_params = {}
    for param_key, value in default_params.items():
        if param_key in ordered:
            ordered[param_key].setdefault("default", str(value))

    return {
        "key": key,
        "name": humanize(key),
        "category": category(key),
        "parameters": ordered,
    }


def build_catalog(notifications: list[dict]) -> dict:
    programs = []
    seen = set()
    for notification in notifications:
        program = parse_notification(notification)
        if not program:
            continue
        if program["key"] in seen:
            continue
        seen.add(program["key"])
        programs.append(program)

    if not programs:
        raise SystemExit("No program notifications found in the input.")

    cat_index = {name: index for index, name in enumerate(CATEGORY_ORDER)}
    programs.sort(
        key=lambda p: (
            cat_index.get(p["category"], len(CATEGORY_ORDER)),
            p["name"].casefold(),
            p["key"],
        )
    )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "hOn Get programs details",
        "brand": BRAND,
        "models": [MODEL],
        "appliance_types": APPLIANCE_TYPES,
        "program_count": len(programs),
        "programs": programs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON with a top-level notifications list")
    parser.add_argument("output", type=Path, help="catalog.json output path")
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    notifications = data.get("notifications", data if isinstance(data, list) else [])
    catalog = build_catalog(notifications)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {catalog['program_count']} programs to {args.output}")


if __name__ == "__main__":
    main()
