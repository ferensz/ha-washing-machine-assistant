"""Diagnostics support for the Washing Machine Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .manager import WashingMachineManager


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return useful state without credentials or personal data."""
    manager: WashingMachineManager = entry.runtime_data
    return {
        "model": manager.model,
        "appliance_type": manager.appliance_type,
        "catalog_version": manager.catalog.get("schema_version"),
        "catalog_generated_at": manager.catalog.get("generated_at"),
        "program_count": len(manager.programs),
        "selected_program": manager.selected_program_key,
        "parameters": manager.snapshot()["parameters"],
        "favorites": {
            name: {
                "program": favorite.get("program"),
                "parameters": favorite.get("parameters"),
                "saved_at": favorite.get("saved_at"),
            }
            for name, favorite in manager._favorites.items()
        },
        "available": manager.available,
    }
