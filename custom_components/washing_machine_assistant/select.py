"""Select entities: program, favorite and enum parameters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import WashingMachineEntity
from .const import (
    CATEGORY_LABELS,
    HIDDEN_PARAMETERS,
    NONE_FAVORITE,
    PARAMETER_ENTITY_IDS,
)
from .coordinator import WashingMachineCoordinator
from .manager import WashingMachineManager
from .util import enum_label_map, enum_value_map


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: WashingMachineManager = entry.runtime_data
    coordinator: WashingMachineCoordinator = manager.coordinator
    entities: list[SelectEntity] = [
        ProgramSelect(coordinator, manager),
        FavoriteSelect(coordinator, manager),
    ]
    for key, spec in manager.union_specs.items():
        if key in HIDDEN_PARAMETERS or spec.get("hidden"):
            continue
        if spec.get("type") == "enum":
            entities.append(ParameterSelect(coordinator, manager, key, spec))
    async_add_entities(entities)


class ProgramSelect(WashingMachineEntity, SelectEntity):
    """Choose one of the appliance programs."""

    _wm_platform = "select"

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="program",
            name="Program",
            icon="mdi:washing-machine",
            suggested_object_id="washing_machine_program",
        )

    @property
    def options(self) -> list[str]:
        return self.manager.program_options

    @property
    def current_option(self) -> str | None:
        return self.manager.program_label

    async def async_select_option(self, option: str) -> None:
        self.manager.select_program(option)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        program = self.manager.current_program
        return {
            "program_key": program["key"],
            "program_name": program["name"],
            "category": program["category"],
            "category_label": CATEGORY_LABELS.get(
                program["category"], program["category"]
            ),
            "parameter_count": len(self.manager.current_visible_parameters),
            "catalog_count": len(self.manager.programs),
        }


class FavoriteSelect(WashingMachineEntity, SelectEntity):
    """Load a saved favorite into the draft."""

    _wm_platform = "select"

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="favorite",
            name="Favorite",
            icon="mdi:star",
            suggested_object_id="washing_machine_favorite",
        )

    @property
    def options(self) -> list[str]:
        return self.manager.favorite_options

    @property
    def current_option(self) -> str | None:
        return self.manager.selected_favorite

    async def async_select_option(self, option: str) -> None:
        if option == NONE_FAVORITE:
            self.manager.clear_favorite_selection()
            return
        self.manager.load_favorite(option)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "favorite_names": self.manager.favorite_names,
            "selected_favorite": self.manager.selected_favorite,
        }


class ParameterSelect(WashingMachineEntity, SelectEntity):
    """An enum parameter for the currently selected program."""

    _wm_platform = "select"

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
        if spec and spec.get("type") == "enum":
            return spec
        return None

    @property
    def available(self) -> bool:
        return super().available and self._spec is not None

    @property
    def options(self) -> list[str]:
        spec = self._spec
        if not spec:
            return []
        return [str(option["label"]) for option in spec.get("options", [])]

    @property
    def current_option(self) -> str | None:
        spec = self._spec
        if not spec:
            return None
        value = self.manager.current_parameters.get(self._key)
        if value is None:
            return None
        return enum_value_map(spec).get(str(value))

    async def async_select_option(self, option: str) -> None:
        spec = self._spec
        if not spec:
            return
        value = enum_label_map(spec).get(option)
        if value is None:
            return
        self.manager.set_parameter(self._key, value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        spec = self._spec
        value = self.manager.current_parameters.get(self._key) if spec else None
        return {
            "parameter_key": self._key,
            "raw_value": value,
        }
