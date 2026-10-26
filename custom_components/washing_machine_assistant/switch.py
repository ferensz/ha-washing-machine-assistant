"""Switch entities for boolean parameters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import WashingMachineEntity
from .const import HIDDEN_PARAMETERS, PARAMETER_ENTITY_IDS
from .coordinator import WashingMachineCoordinator
from .manager import WashingMachineManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: WashingMachineManager = entry.runtime_data
    coordinator: WashingMachineCoordinator = manager.coordinator
    entities: list[SwitchEntity] = []
    for key, spec in manager.union_specs.items():
        if key in HIDDEN_PARAMETERS or spec.get("hidden"):
            continue
        if spec.get("type") == "bool":
            entities.append(ParameterSwitch(coordinator, manager, key, spec))
    async_add_entities(entities)


class ParameterSwitch(WashingMachineEntity, SwitchEntity):
    """A 0/1 parameter for the currently selected program."""

    _wm_platform = "switch"

    def __init__(
        self,
        coordinator: WashingMachineCoordinator,
        manager: WashingMachineManager,
        key: str,
        spec: dict[str, Any],
    ) -> None:
        self._key = key
        super().__init__(
            coordinator,
            manager,
            key=key,
            name=spec.get("title", key),
            icon=spec.get("icon"),
            suggested_object_id=PARAMETER_ENTITY_IDS.get(
                key, f"washing_machine_{key}"
            ),
        )

    @property
    def _spec(self) -> dict[str, Any] | None:
        spec = self.manager.current_program.get("parameters", {}).get(self._key)
        if spec and spec.get("type") == "bool":
            return spec
        return None

    @property
    def available(self) -> bool:
        return super().available and self._spec is not None

    @property
    def is_on(self) -> bool:
        return str(self.manager.current_parameters.get(self._key, "0")) == "1"

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.manager.set_parameter(self._key, "1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.manager.set_parameter(self._key, "0")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"parameter_key": self._key}
