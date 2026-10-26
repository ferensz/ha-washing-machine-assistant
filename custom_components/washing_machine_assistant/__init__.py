"""Set up the Washing Machine Assistant integration."""

from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .catalog import CatalogError, load_catalog
from .const import (
    CONF_APPLIANCE_TYPE,
    CONF_DEVICE_ID,
    CONF_HON_ENTRY_ID,
    CONF_MAC,
    CONF_MODEL,
    DOMAIN,
    PLATFORMS,
    SERVICE_DELETE_FAVORITE,
    SERVICE_LOAD_FAVORITE,
    SERVICE_SAVE_FAVORITE,
    SERVICE_START,
    SERVICE_START_FAVORITE,
    SERVICE_STOP,
)
from .coordinator import WashingMachineCoordinator
from .manager import WashingMachineManager

_LOGGER = logging.getLogger(__name__)

DATA_STATIC = f"{DOMAIN}_static_path"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services and the card's static path once."""
    hass.data.setdefault(DOMAIN, {})

    if not hass.data.get(DATA_STATIC):
        if hass.http is None:
            _LOGGER.warning("HTTP is not set up; the custom card will not be served")
        else:
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        f"/{DOMAIN}",
                        str(Path(__file__).parent / "www"),
                        cache_headers=False,
                    )
                ]
            )
            hass.data[DATA_STATIC] = True

    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one washing machine."""
    try:
        catalog = load_catalog()
    except CatalogError as err:
        raise ConfigEntryNotReady(str(err)) from err

    hon_entry_id = entry.data[CONF_HON_ENTRY_ID]
    hon_entry = hass.config_entries.async_get_entry(hon_entry_id)
    if hon_entry is None or hon_entry.state is not ConfigEntryState.LOADED:
        raise ConfigEntryNotReady("The hOn integration is not loaded")
    if not hass.services.has_service("hon", "start_program"):
        raise ConfigEntryNotReady("The hOn start_program service is not available")

    device_id = entry.data[CONF_DEVICE_ID]
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ConfigEntryNotReady("The hOn washing machine device no longer exists")

    model = str(device.model or entry.data.get(CONF_MODEL) or "")
    supported = {str(item).casefold() for item in catalog.get("models", [])}
    if model.casefold() not in supported:
        raise ConfigEntryNotReady(
            f"Unsupported model {model!r}; catalog supports {catalog.get('models')}"
        )

    manager = WashingMachineManager(
        hass,
        entry,
        catalog,
        hon_entry_id=hon_entry_id,
        hon_device_id=device_id,
        mac=entry.data[CONF_MAC],
        appliance_type=entry.data[CONF_APPLIANCE_TYPE],
        model=model,
    )
    await manager.async_setup()

    coordinator = WashingMachineCoordinator(hass, manager)
    await coordinator.async_config_entry_first_refresh()
    manager.attach_coordinator(coordinator)
    entry.runtime_data = manager
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_hon_updated(
        changed_hass: HomeAssistant, changed_entry: ConfigEntry
    ) -> None:
        manager._notify()

    entry.async_on_unload(hon_entry.add_update_listener(_async_hon_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        manager: WashingMachineManager | None = hass.data.get(DOMAIN, {}).pop(
            entry.entry_id, None
        )
        if manager is not None:
            await manager.async_unload()
    return unloaded


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the integration services if they are not registered yet."""
    if hass.services.has_service(DOMAIN, SERVICE_START):
        return

    base_schema = {
        vol.Optional(CONF_DEVICE_ID): vol.Any(cv.string, list),
    }
    start_schema = vol.Schema(
        {
            **base_schema,
            vol.Optional("program"): cv.string,
            vol.Optional("parameters"): vol.Any(dict, cv.string),
            vol.Optional("dry_run", default=False): cv.boolean,
        }
    )
    favorite_schema = vol.Schema(
        {
            **base_schema,
            vol.Required("name"): cv.string,
            vol.Optional("program"): cv.string,
            vol.Optional("parameters"): vol.Any(dict, cv.string),
        }
    )
    favorite_name_schema = vol.Schema(
        {
            **base_schema,
            vol.Required("name"): cv.string,
        }
    )
    stop_schema = vol.Schema(base_schema)

    async def _handle_start(call: ServiceCall) -> dict[str, Any] | None:
        manager = _get_manager(hass, call)
        parameters = _parse_parameters(call.data.get("parameters"))
        program = call.data.get("program")
        if program:
            manager.select_program(program)
        if parameters:
            for key, value in parameters.items():
                manager.set_parameter(key, value)
        if call.data.get("dry_run"):
            return manager.build_payload()
        return await manager.async_start()

    async def _handle_stop(call: ServiceCall) -> None:
        await _get_manager(hass, call).async_stop()

    async def _handle_load_favorite(call: ServiceCall) -> None:
        _get_manager(hass, call).load_favorite(call.data["name"])

    async def _handle_start_favorite(call: ServiceCall) -> dict[str, Any]:
        return await _get_manager(hass, call).async_start_favorite(call.data["name"])

    async def _handle_save_favorite(call: ServiceCall) -> dict[str, Any]:
        manager = _get_manager(hass, call)
        parameters = _parse_parameters(call.data.get("parameters"))
        program = call.data.get("program")
        if program:
            manager.select_program(program)
        if parameters:
            for key, value in parameters.items():
                manager.set_parameter(key, value)
        name = await manager.save_favorite(call.data["name"])
        return {"name": name}

    async def _handle_delete_favorite(call: ServiceCall) -> None:
        await _get_manager(hass, call).delete_favorite(call.data["name"])

    hass.services.async_register(
        DOMAIN,
        SERVICE_START,
        _handle_start,
        schema=start_schema,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP, _handle_stop, schema=stop_schema
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOAD_FAVORITE,
        _handle_load_favorite,
        schema=favorite_name_schema,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_FAVORITE,
        _handle_start_favorite,
        schema=favorite_name_schema,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SAVE_FAVORITE,
        _handle_save_favorite,
        schema=favorite_schema,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_FAVORITE,
        _handle_delete_favorite,
        schema=favorite_name_schema,
    )


def _get_manager(hass: HomeAssistant, call: ServiceCall) -> WashingMachineManager:
    managers: list[WashingMachineManager] = list(hass.data.get(DOMAIN, {}).values())
    if not managers:
        raise ServiceValidationError("No washing machine is configured")
    device_id = call.data.get(CONF_DEVICE_ID)
    if isinstance(device_id, (list, tuple)):
        device_id = device_id[0] if len(device_id) == 1 else None
    if device_id:
        for manager in managers:
            if manager.hon_device_id == device_id or manager.entry.entry_id == device_id:
                return manager
        registry = dr.async_get(hass)
        for manager in managers:
            device = registry.async_get_device(
                identifiers={(DOMAIN, manager.entry.entry_id)}
            )
            if device is not None and device.id == device_id:
                return manager
        raise ServiceValidationError(f"Unknown washing machine device: {device_id}")
    if len(managers) == 1:
        return managers[0]
    raise ServiceValidationError(
        "Multiple washing machines are configured; specify device_id"
    )


def _parse_parameters(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as err:
                raise ServiceValidationError(
                    f"parameters must be a mapping or a valid dict string: {err}"
                ) from err
        if not isinstance(parsed, dict):
            raise ServiceValidationError("parameters must be a mapping")
        return parsed
    raise ServiceValidationError("parameters must be a mapping or a dict string")
