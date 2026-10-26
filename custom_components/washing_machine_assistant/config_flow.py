"""Config flow for the Washing Machine Assistant."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .catalog import CatalogError, load_catalog
from .const import (
    CONF_APPLIANCE_TYPE,
    CONF_DEVICE_ID,
    CONF_HON_ENTRY_ID,
    CONF_MAC,
    CONF_MODEL,
    DOMAIN,
    NAME,
)

_LOGGER = logging.getLogger(__name__)


class WashingMachineAssistantConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pick one hOn washing machine."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        hon_entries = self.hass.config_entries.async_entries("hon")
        if not hon_entries:
            return self.async_abort(reason="hon_not_configured")

        hon_entry_ids = {entry.entry_id for entry in hon_entries}
        device_registry = dr.async_get(self.hass)
        devices: dict[str, str] = {}
        for hon_entry in hon_entries:
            for device in dr.async_entries_for_config_entry(
                device_registry, hon_entry.entry_id
            ):
                identifier = next(
                    (
                        item
                        for item in device.identifiers
                        if len(item) >= 3
                        and item[0] == "hon"
                        and item[2] in {"WM", "WD"}
                    ),
                    None,
                )
                if identifier is None:
                    continue
                name = device.name_by_user or device.name
                model = device.model or "unknown model"
                devices[device.id] = f"{name} ({model})"

        if not devices:
            return self.async_abort(reason="no_washing_machine")

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_ID, default=next(iter(devices))
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=key, label=value)
                                for key, value in devices.items()
                            ]
                        )
                    )
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)

        device_id = user_input[CONF_DEVICE_ID]
        device = device_registry.async_get(device_id)
        if device is None:
            errors["base"] = "device_not_found"
        else:
            identifier = next(
                (
                    item
                    for item in device.identifiers
                    if len(item) >= 3
                    and item[0] == "hon"
                    and item[2] in {"WM", "WD"}
                ),
                None,
            )
            if identifier is None:
                errors["base"] = "device_not_found"
            else:
                try:
                    catalog = load_catalog()
                except CatalogError as err:
                    _LOGGER.error("Cannot load catalog: %s", err)
                    errors["base"] = "catalog_missing"
                else:
                    model = (device.model or "").strip()
                    supported = {
                        str(item).casefold() for item in catalog.get("models", [])
                    }
                    if model.casefold() not in supported:
                        return self.async_abort(
                            reason="unsupported_model",
                            description_placeholders={
                                "model": model or "unknown",
                                "models": ", ".join(catalog.get("models", [])),
                            },
                        )
                    hon_entry_id = next(
                        (
                            entry_id
                            for entry_id in device.config_entries
                            if entry_id in hon_entry_ids
                        ),
                        None,
                    )
                    if hon_entry_id is None:
                        errors["base"] = "hon_entry_not_found"
                    else:
                        await self.async_set_unique_id(device_id)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=device.name_by_user or device.name or NAME,
                            data={
                                CONF_DEVICE_ID: device.id,
                                CONF_HON_ENTRY_ID: hon_entry_id,
                                CONF_MAC: identifier[1],
                                CONF_APPLIANCE_TYPE: identifier[2],
                                CONF_MODEL: model,
                            },
                        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_ID,
                    default=device_id if device_id in devices else next(iter(devices)),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=key, label=value)
                            for key, value in devices.items()
                        ]
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
