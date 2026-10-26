"""Text entity for the favorite name input."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import WashingMachineEntity
from .const import FAVORITE_NAME_MAX
from .coordinator import WashingMachineCoordinator
from .manager import WashingMachineManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: WashingMachineManager = entry.runtime_data
    coordinator: WashingMachineCoordinator = manager.coordinator
    async_add_entities([FavoriteNameText(coordinator, manager)])


class FavoriteNameText(WashingMachineEntity, TextEntity):
    """Holds the name used by the Save favorite button."""

    _wm_platform = "text"

    _attr_mode = TextMode.TEXT

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="favorite_name",
            name="Favorite name",
            icon="mdi:star-outline",
            suggested_object_id="washing_machine_favorite_name",
        )
        self._attr_native_min = 0
        self._attr_native_max = FAVORITE_NAME_MAX

    @property
    def native_value(self) -> str:
        return self.manager.favorite_name

    async def async_set_value(self, value: str) -> None:
        self.manager.set_favorite_name(value)
