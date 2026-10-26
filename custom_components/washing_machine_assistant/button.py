"""Buttons for starting, stopping and managing favorites."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import WashingMachineEntity
from .const import NONE_FAVORITE
from .coordinator import WashingMachineCoordinator
from .manager import WashingMachineManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: WashingMachineManager = entry.runtime_data
    coordinator: WashingMachineCoordinator = manager.coordinator
    async_add_entities(
        [
            StartButton(coordinator, manager),
            StopButton(coordinator, manager),
            StartFavoriteButton(coordinator, manager),
            SaveFavoriteButton(coordinator, manager),
            DeleteFavoriteButton(coordinator, manager),
        ]
    )


class StartButton(WashingMachineEntity, ButtonEntity):
    """Start the current draft."""

    _wm_platform = "button"

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="start",
            name="Start cycle",
            icon="mdi:play",
            suggested_object_id="washing_machine_start",
        )

    async def async_press(self) -> None:
        await self.manager.async_start()


class StopButton(WashingMachineEntity, ButtonEntity):
    """Stop the current cycle."""

    _wm_platform = "button"

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="stop",
            name="Stop cycle",
            icon="mdi:stop",
            suggested_object_id="washing_machine_stop",
        )

    async def async_press(self) -> None:
        await self.manager.async_stop()


class StartFavoriteButton(WashingMachineEntity, ButtonEntity):
    """Start the selected favorite."""

    _wm_platform = "button"

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="start_favorite",
            name="Start favorite",
            icon="mdi:play-circle",
            suggested_object_id="washing_machine_start_favorite",
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.manager.selected_favorite != NONE_FAVORITE
        )

    async def async_press(self) -> None:
        await self.manager.async_start_favorite()


class SaveFavoriteButton(WashingMachineEntity, ButtonEntity):
    """Save the current draft under the name in the favorite-name field."""

    _wm_platform = "button"

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="save_favorite",
            name="Save favorite",
            icon="mdi:content-save",
            suggested_object_id="washing_machine_save_favorite",
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self.manager.favorite_name.strip())

    async def async_press(self) -> None:
        await self.manager.save_favorite()


class DeleteFavoriteButton(WashingMachineEntity, ButtonEntity):
    """Delete the selected favorite."""

    _wm_platform = "button"

    def __init__(
        self, coordinator: WashingMachineCoordinator, manager: WashingMachineManager
    ) -> None:
        super().__init__(
            coordinator,
            manager,
            key="delete_favorite",
            name="Delete favorite",
            icon="mdi:delete",
            suggested_object_id="washing_machine_delete_favorite",
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.manager.selected_favorite != NONE_FAVORITE
        )

    async def async_press(self) -> None:
        await self.manager.delete_favorite()
