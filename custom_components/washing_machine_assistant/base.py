"""Common entity base for the Washing Machine Assistant."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WashingMachineCoordinator
from .manager import WashingMachineManager


class WashingMachineEntity(CoordinatorEntity[WashingMachineCoordinator]):
    """Base entity tied to one washing machine manager."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _wm_platform = ""

    def __init__(
        self,
        coordinator: WashingMachineCoordinator,
        manager: WashingMachineManager,
        *,
        key: str,
        name: str,
        icon: str | None = None,
        suggested_object_id: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.manager = manager
        self._attr_unique_id = manager.unique_id(key)
        self._attr_name = name
        self._attr_icon = icon
        if self._wm_platform:
            self.entity_id = (
                f"{self._wm_platform}."
                f"{suggested_object_id or f'washing_machine_{key}'}"
            )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.entry.entry_id)},
            name="Washing machine controls",
            manufacturer="hOn",
            model=manager.model,
        )

    @property
    def available(self) -> bool:
        return super().available and self.manager.available
