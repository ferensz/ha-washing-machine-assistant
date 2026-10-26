"""Single control sensor consumed by the custom Lovelace card."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import WashingMachineEntity
from .coordinator import WashingMachineCoordinator
from .manager import WashingMachineManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: WashingMachineManager = entry.runtime_data
    coordinator: WashingMachineCoordinator = manager.coordinator
    async_add_entities([ControlsSensor(coordinator, manager)])


class ControlsSensor(WashingMachineEntity, SensorEntity):
    """Expose the manager snapshot for the card and for dashboards."""

    _wm_platform = "sensor"

    _attr_icon = "mdi:washing-machine"
    # These change often or are large; keep them out of the recorder.
    _unrecorded_attributes = frozenset(
        {"programs", "parameter_schema", "parameters", "parameter_entities"}
    )

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="controls",
            name="Overview",
            icon="mdi:washing-machine",
            suggested_object_id="washing_machine_controls",
        )

    @property
    def native_value(self) -> str:
        return self.manager.program_label

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.manager.snapshot()
