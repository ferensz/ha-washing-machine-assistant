"""Coordinator bridging the manager's draft state to HA entities."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import NAME
from .manager import WashingMachineManager

_LOGGER = logging.getLogger(__name__)


class WashingMachineCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """No polling: the manager pushes snapshots into the coordinator."""

    def __init__(self, hass: HomeAssistant, manager: WashingMachineManager) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=manager.entry,
            name=f"{NAME} {manager.entry.title}",
            update_interval=None,
        )
        self.manager = manager

    async def _async_update_data(self) -> dict[str, Any]:
        return self.manager.snapshot()
