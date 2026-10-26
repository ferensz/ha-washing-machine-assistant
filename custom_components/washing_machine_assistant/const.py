"""Constants for the Washing Machine Assistant integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.const import Platform

DOMAIN = "washing_machine_assistant"
NAME = "Washing Machine Assistant"
VERSION = "0.1.0"

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

CONF_DEVICE_ID = "device_id"
CONF_HON_ENTRY_ID = "hon_entry_id"
CONF_MAC = "mac"
CONF_APPLIANCE_TYPE = "appliance_type"
CONF_MODEL = "model"

CATALOG_PATH = Path(__file__).parent / "catalog.json"
STORAGE_VERSION = 1
STORAGE_MINOR_VERSION = 1

DEFAULT_PROGRAM = "iot_wash_cotton"
NONE_FAVORITE = "None"
FAVORITE_NAME_MAX = 40

HIDDEN_PARAMETERS = frozenset({"lang"})

# Order used for the entity list and the card. Unknown parameters go last.
PARAMETER_ORDER = [
    "temp",
    "spinSpeed",
    "delayTime",
    "prewash",
    "hygiene",
    "anticrease",
    "goodNight",
    "extraRinse1",
    "extraRinse2",
    "extraRinse3",
    "acquaplus",
    "dirtyLevel",
    "steamLevel",
    "lang",
]

PARAMETER_ENTITY_IDS = {
    "temp": "washing_machine_temperature",
    "spinSpeed": "washing_machine_spin_speed",
    "delayTime": "washing_machine_delay_time",
    "prewash": "washing_machine_prewash",
    "hygiene": "washing_machine_hygiene",
    "anticrease": "washing_machine_anti_crease",
    "goodNight": "washing_machine_good_night",
    "extraRinse1": "washing_machine_extra_rinse_1",
    "extraRinse2": "washing_machine_extra_rinse_2",
    "extraRinse3": "washing_machine_extra_rinse_3",
    "acquaplus": "washing_machine_aqua_plus",
    "dirtyLevel": "washing_machine_soiling_level",
    "steamLevel": "washing_machine_steam_level",
}

ENTITY_PROGRAM = "select.washing_machine_program"
ENTITY_FAVORITE = "select.washing_machine_favorite"
ENTITY_FAVORITE_NAME = "text.washing_machine_favorite_name"
ENTITY_START = "button.washing_machine_start"
ENTITY_STOP = "button.washing_machine_stop"
ENTITY_START_FAVORITE = "button.washing_machine_start_favorite"
ENTITY_SAVE_FAVORITE = "button.washing_machine_save_favorite"
ENTITY_DELETE_FAVORITE = "button.washing_machine_delete_favorite"
ENTITY_CONTROLS = "sensor.washing_machine_controls"

CATEGORY_LABELS = {
    "everyday": "Everyday",
    "special": "Special care",
    "stains": "Stains",
    "branded": "Branded",
    "steam": "Steam",
    "extras": "Extras",
}

SERVICE_START = "start"
SERVICE_STOP = "stop"
SERVICE_LOAD_FAVORITE = "load_favorite"
SERVICE_START_FAVORITE = "start_favorite"
SERVICE_SAVE_FAVORITE = "save_favorite"
SERVICE_DELETE_FAVORITE = "delete_favorite"
