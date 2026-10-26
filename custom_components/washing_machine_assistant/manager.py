"""Runtime state and actions for one washing machine."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .catalog import (
    build_program_maps,
    ordered_parameters,
    programs_payload,
    union_parameter_specs,
)
from .const import (
    DEFAULT_PROGRAM,
    DOMAIN,
    ENTITY_CONTROLS,
    ENTITY_DELETE_FAVORITE,
    ENTITY_FAVORITE,
    ENTITY_FAVORITE_NAME,
    ENTITY_PROGRAM,
    ENTITY_SAVE_FAVORITE,
    ENTITY_START,
    ENTITY_START_FAVORITE,
    ENTITY_STOP,
    FAVORITE_NAME_MAX,
    HIDDEN_PARAMETERS,
    NONE_FAVORITE,
    PARAMETER_ENTITY_IDS,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)
from .util import (
    ParameterValidationError,
    coerce_params,
    defaults_for,
    normalize_value,
    parameter_summary,
)

_LOGGER = logging.getLogger(__name__)


def _platform_for(spec: dict[str, Any]) -> str:
    kind = spec.get("type")
    if kind == "enum":
        return "select"
    if kind == "bool":
        return "switch"
    return "number"


class WashingMachineManager:
    """Owns the draft selection, favorites and the hOn service calls."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        catalog: dict[str, Any],
        *,
        hon_entry_id: str,
        hon_device_id: str,
        mac: str,
        appliance_type: str,
        model: str,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.catalog = catalog
        self.programs = catalog["programs"]
        self.by_key, self.label_by_key, self.key_by_label, self.program_options = (
            build_program_maps(self.programs)
        )
        self.union_specs = union_parameter_specs(self.programs)
        self.programs_payload = programs_payload(self.programs, self.label_by_key)
        self.hon_entry_id = hon_entry_id
        self.hon_device_id = hon_device_id
        self.mac = mac
        self.appliance_type = appliance_type
        self.model = model

        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{hon_device_id}",
            minor_version=STORAGE_MINOR_VERSION,
        )
        self._favorites: dict[str, dict[str, Any]] = {}
        self._selected_favorite: str | None = None
        self._favorite_name = ""

        first_key = (
            DEFAULT_PROGRAM if DEFAULT_PROGRAM in self.by_key else self.programs[0]["key"]
        )
        self._selected_program_key = first_key
        self._params = defaults_for(self.current_program)
        self.coordinator = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        data = await self._store.async_load()
        if isinstance(data, dict):
            favorites = data.get("favorites")
            if isinstance(favorites, dict):
                for name, favorite in favorites.items():
                    if (
                        isinstance(favorite, dict)
                        and favorite.get("program") in self.by_key
                        and isinstance(favorite.get("parameters"), dict)
                    ):
                        self._favorites[str(name)] = favorite
                    else:
                        _LOGGER.warning(
                            "Ignoring invalid favorite %r for %s", name, self.entry.title
                        )
            last = data.get("last_selection")
            if isinstance(last, dict) and last.get("program") in self.by_key:
                self._selected_program_key = str(last["program"])
                self._params = coerce_params(
                    self.current_program, last.get("parameters"), strict=False
                )
        _LOGGER.debug(
            "Loaded %s programs and %s favorites for %s",
            len(self.programs),
            len(self._favorites),
            self.entry.title,
        )

    async def async_unload(self) -> None:
        try:
            await self._store.async_save(self._data_to_save())
        except Exception:
            _LOGGER.exception("Could not save washing machine state during unload")

    def attach_coordinator(self, coordinator) -> None:
        self.coordinator = coordinator
        self._notify()

    # ------------------------------------------------------------------
    # Snapshot used by entities and the card
    # ------------------------------------------------------------------
    @property
    def current_program(self) -> dict[str, Any]:
        return self.by_key[self._selected_program_key]

    @property
    def program_label(self) -> str:
        return self.label_by_key[self._selected_program_key]

    @property
    def selected_program_key(self) -> str:
        return self._selected_program_key

    @property
    def favorite_names(self) -> list[str]:
        return sorted(self._favorites, key=str.casefold)

    @property
    def favorite_options(self) -> list[str]:
        return [NONE_FAVORITE, *self.favorite_names]

    @property
    def selected_favorite(self) -> str:
        return self._selected_favorite or NONE_FAVORITE

    @property
    def favorite_name(self) -> str:
        return self._favorite_name

    @property
    def available(self) -> bool:
        if not self.hass.services.has_service("hon", "start_program"):
            return False
        entry = self.hass.config_entries.async_get_entry(self.hon_entry_id)
        return bool(entry and entry.state is ConfigEntryState.LOADED)

    @property
    def current_visible_parameters(self) -> dict[str, dict[str, Any]]:
        return ordered_parameters(self.current_program)

    @property
    def current_parameters(self) -> dict[str, str]:
        return {
            key: self._params.get(key, spec.get("default", "0"))
            for key, spec in self.current_visible_parameters.items()
        }

    def parameter_schema(self) -> dict[str, dict[str, Any]]:
        """The current program's visible parameter specs."""
        return ordered_parameters(self.current_program)

    def parameter_entity_ids(self) -> dict[str, str]:
        """Resolve the actual entity IDs from the registry, with a fallback."""
        registry = er.async_get(self.hass)
        result: dict[str, str] = {}
        for key, spec in self.union_specs.items():
            if key in HIDDEN_PARAMETERS or spec.get("hidden"):
                continue
            platform = _platform_for(spec)
            unique_id = self.unique_id(key)
            entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
            if not entity_id:
                suggested = PARAMETER_ENTITY_IDS.get(key, f"washing_machine_{key}")
                entity_id = f"{platform}.{suggested}"
            result[key] = entity_id
        return result

    def unique_id(self, suffix: str) -> str:
        return f"{self.hon_device_id}_{suffix}"

    def entity_id(self, platform: str, suffix: str, fallback: str) -> str:
        registry = er.async_get(self.hass)
        entity_id = registry.async_get_entity_id(platform, DOMAIN, self.unique_id(suffix))
        return entity_id or fallback

    def entities_payload(self) -> dict[str, str]:
        return {
            "program": self.entity_id("select", "program", ENTITY_PROGRAM),
            "favorite": self.entity_id("select", "favorite", ENTITY_FAVORITE),
            "favorite_name": self.entity_id(
                "text", "favorite_name", ENTITY_FAVORITE_NAME
            ),
            "start": self.entity_id("button", "start", ENTITY_START),
            "stop": self.entity_id("button", "stop", ENTITY_STOP),
            "start_favorite": self.entity_id(
                "button", "start_favorite", ENTITY_START_FAVORITE
            ),
            "save_favorite": self.entity_id(
                "button", "save_favorite", ENTITY_SAVE_FAVORITE
            ),
            "delete_favorite": self.entity_id(
                "button", "delete_favorite", ENTITY_DELETE_FAVORITE
            ),
            "controls": self.entity_id("sensor", "controls", ENTITY_CONTROLS),
        }

    def snapshot(self) -> dict[str, Any]:
        program = self.current_program
        visible = ordered_parameters(program)
        return {
            "program_key": self._selected_program_key,
            "program_name": program["name"],
            "program_label": self.program_label,
            "program_category": program["category"],
            "programs": self.programs_payload,
            "parameter_schema": visible,
            "parameter_entities": self.parameter_entity_ids(),
            "parameters": {
                key: self._params.get(key, spec.get("default", "0"))
                for key, spec in visible.items()
            },
            "summary": parameter_summary(program, self._params),
            "favorite_names": self.favorite_names,
            "favorite_options": self.favorite_options,
            "selected_favorite": self.selected_favorite,
            "favorite_name": self._favorite_name,
            "entities": self.entities_payload(),
            "device_id": self.hon_device_id,
            "model": self.model,
            "catalog_count": len(self.programs),
            "catalog_version": self.catalog.get("schema_version"),
            "catalog_generated_at": self.catalog.get("generated_at"),
        }

    # ------------------------------------------------------------------
    # Draft changes
    # ------------------------------------------------------------------
    def select_program(self, label_or_key: str) -> None:
        key = self.key_by_label.get(label_or_key)
        if key is None and label_or_key in self.by_key:
            key = label_or_key
        if key is None:
            raise ServiceValidationError(f"Unknown program {label_or_key!r}")
        if key == self._selected_program_key:
            return
        program = self.by_key[key]
        # Keep settings that exist on both programs and are valid; use the new
        # program's defaults for everything else.
        self._params = coerce_params(program, self._params, strict=False)
        self._selected_program_key = key
        self._selected_favorite = None
        self._notify()
        self._schedule_save()

    def set_parameter(self, key: str, value: Any) -> None:
        spec = self.current_program.get("parameters", {}).get(key)
        if spec is None or key in HIDDEN_PARAMETERS or spec.get("hidden"):
            raise ServiceValidationError(
                f"Parameter {key!r} is not available for {self.program_label}"
            )
        try:
            normalized = normalize_value(spec, value)
        except ParameterValidationError as err:
            raise ServiceValidationError(
                f"{spec.get('title', key)}: {err}"
            ) from err
        if self._params.get(key) == normalized:
            return
        self._params[key] = normalized
        self._selected_favorite = None
        self._notify()
        self._schedule_save()

    def set_favorite_name(self, value: str) -> None:
        self._favorite_name = (value or "").strip()[:FAVORITE_NAME_MAX]
        self._notify()

    def clear_favorite_selection(self) -> None:
        if self._selected_favorite is None:
            return
        self._selected_favorite = None
        self._notify()

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------
    def _find_favorite(self, name: str) -> str | None:
        wanted = (name or "").strip().casefold()
        for existing in self._favorites:
            if existing.casefold() == wanted:
                return existing
        return None

    def load_favorite(self, name: str) -> None:
        canonical = self._find_favorite(name)
        if canonical is None:
            raise ServiceValidationError(f"Favorite {name!r} does not exist")
        favorite = self._favorites[canonical]
        program_key = favorite.get("program")
        if program_key not in self.by_key:
            raise ServiceValidationError(
                f"Favorite {name!r} uses a program that is no longer in the catalog"
            )
        self._selected_program_key = str(program_key)
        self._params = coerce_params(
            self.current_program, favorite.get("parameters"), strict=False
        )
        self._selected_favorite = canonical
        self._favorite_name = canonical
        self._notify()
        self._schedule_save()

    async def save_favorite(self, name: str | None = None) -> str:
        raw_name = (name if name is not None else self._favorite_name).strip()
        if not raw_name:
            raise ServiceValidationError("Enter a favorite name first")
        if len(raw_name) > FAVORITE_NAME_MAX:
            raise ServiceValidationError(
                f"Favorite names are limited to {FAVORITE_NAME_MAX} characters"
            )
        if raw_name.casefold() == NONE_FAVORITE.casefold():
            raise ServiceValidationError(
                f"{NONE_FAVORITE!r} is reserved; choose another favorite name"
            )
        canonical = self._find_favorite(raw_name) or raw_name
        self._favorites[canonical] = {
            "program": self._selected_program_key,
            "parameters": dict(self._params),
            "saved_at": datetime.now(UTC).isoformat(),
        }
        self._selected_favorite = canonical
        self._favorite_name = canonical
        await self._store.async_save(self._data_to_save())
        self._notify()
        return canonical

    async def delete_favorite(self, name: str | None = None) -> None:
        target = name if name is not None else self.selected_favorite
        if not target or target == NONE_FAVORITE:
            raise ServiceValidationError("Select a favorite to delete")
        canonical = self._find_favorite(target)
        if canonical is None:
            raise ServiceValidationError(f"Favorite {target!r} does not exist")
        self._favorites.pop(canonical, None)
        if self._selected_favorite == canonical:
            self._selected_favorite = None
        if self._favorite_name == canonical:
            self._favorite_name = ""
        await self._store.async_save(self._data_to_save())
        self._notify()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def build_payload(self) -> dict[str, Any]:
        program = self.current_program
        try:
            parameters = coerce_params(program, self._params, strict=True)
        except ParameterValidationError as err:
            raise ServiceValidationError(f"Invalid settings: {err}") from err
        return {
            "program": program["key"],
            "parameters": parameters,
            "summary": parameter_summary(program, parameters),
        }

    async def async_start(self) -> dict[str, Any]:
        payload = self.build_payload()
        _LOGGER.debug(
            "Starting %s on %s with %s",
            payload["program"],
            self.entry.title,
            payload["parameters"],
        )
        try:
            await self.hass.services.async_call(
                "hon",
                "start_program",
                {
                    "device_id": [self.hon_device_id],
                    "program": payload["program"],
                    "parameters": str(payload["parameters"]),
                },
                blocking=True,
            )
        except HomeAssistantError as err:
            raise HomeAssistantError(
                f"hOn rejected the program: {err}"
            ) from err
        self._schedule_save()
        return payload

    async def async_stop(self) -> None:
        try:
            await self.hass.services.async_call(
                "hon",
                "turn_off",
                {"device": self.hon_device_id},
                blocking=True,
            )
        except HomeAssistantError as err:
            raise HomeAssistantError(f"hOn could not stop the cycle: {err}") from err

    async def async_start_favorite(self, name: str | None = None) -> dict[str, Any]:
        target = name if name is not None else self.selected_favorite
        if not target or target == NONE_FAVORITE:
            raise ServiceValidationError("Select a favorite to start")
        self.load_favorite(target)
        return await self.async_start()

    # ------------------------------------------------------------------
    # Persistence / notifications
    # ------------------------------------------------------------------
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "favorites": self._favorites,
            "last_selection": {
                "program": self._selected_program_key,
                "parameters": dict(self._params),
            },
        }

    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._data_to_save, 5)

    def _notify(self) -> None:
        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(self.snapshot())
