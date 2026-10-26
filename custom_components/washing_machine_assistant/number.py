"""Number entities for range parameters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
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
    entities: list[NumberEntity] = []
    for key, spec in manager.union_specs.items():
        if key in HIDDEN_PARAMETERS or spec.get("hidden"):
            continue
        if spec.get("type") == "range":
            entities.append(ParameterNumber(coordinator, manager, key, spec))
    async_add_entities(entities)


class ParameterNumber(WashingMachineEntity, NumberEntity):
    """A range parameter for the currently selected program."""

    _wm_platform = "number"

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
        self._attr_mode = NumberMode.SLIDER

    @property
    def _spec(self) -> dict[str, Any] | None:
        spec = self.manager.current_program.get("parameters", {}).get(self._key)
        if spec and spec.get("type") == "range":
            return spec
        return None

    @property
    def available(self) -> bool:
        return super().available and self._spec is not None

    @property
    def native_value(self) -> float | None:
        if self._spec is None:
            return None
        value = self.manager.current_parameters.get(self._key)
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    @property
    def native_min_value(self) -> float:
        spec = self._spec
        return float(spec["min"]) if spec else 0.0

    @property
    def native_max_value(self) -> float:
        spec = self._spec
        return float(spec["max"]) if spec else 0.0

    @property
    def native_step(self) -> float:
        spec = self._spec
        return float(spec.get("step", 1)) if spec else 1.0

    @property
    def native_unit_of_measurement(self) -> str | None:
        spec = self._spec
        return spec.get("unit") if spec else None

    async def async_set_native_value(self, value: float) -> None:
        self.manager.set_parameter(self._key, value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"parameter_key": self._key}
