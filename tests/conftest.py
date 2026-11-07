"""Stub out homeassistant imports so tests run without a full HA installation."""
import sys
import types
from enum import Enum
from unittest.mock import MagicMock


def _make_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# --- homeassistant.exceptions ---
class HomeAssistantError(Exception):
    pass

class ConfigEntryNotReady(HomeAssistantError):
    pass

_make_module(
    "homeassistant.exceptions",
    HomeAssistantError=HomeAssistantError,
    ConfigEntryNotReady=ConfigEntryNotReady,
)

# --- homeassistant.const ---
class UnitOfTemperature:
    CELSIUS = "°C"
    FAHRENHEIT = "°F"

ATTR_TEMPERATURE = "temperature"
_make_module("homeassistant.const", UnitOfTemperature=UnitOfTemperature, ATTR_TEMPERATURE=ATTR_TEMPERATURE)

# --- homeassistant.components.climate ---
class HVACMode(str, Enum):
    OFF = "off"
    AUTO = "auto"
    COOL = "cool"
    HEAT = "heat"
    DRY = "dry"
    FAN_ONLY = "fan_only"

class ClimateEntityFeature(int, Enum):
    TARGET_TEMPERATURE = 1
    FAN_MODE = 2
    SWING_MODE = 4
    TURN_ON = 8
    TURN_OFF = 16

class ClimateEntity:
    pass

_make_module(
    "homeassistant.components.climate",
    ClimateEntity=ClimateEntity,
    ClimateEntityFeature=ClimateEntityFeature,
    HVACMode=HVACMode,
)
_make_module("homeassistant.components", climate=sys.modules["homeassistant.components.climate"])

# --- homeassistant.helpers.update_coordinator ---
class DataUpdateCoordinator:
    def __init__(self, hass, logger, *, name, update_interval):
        self.data = None

    def __class_getitem__(cls, item):
        return cls

class CoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    def __class_getitem__(cls, item):
        return cls

class UpdateFailed(Exception):
    pass

_make_module(
    "homeassistant.helpers.update_coordinator",
    DataUpdateCoordinator=DataUpdateCoordinator,
    CoordinatorEntity=CoordinatorEntity,
    UpdateFailed=UpdateFailed,
)

# --- homeassistant.helpers.entity ---
class DeviceInfo(dict):
    pass

_make_module("homeassistant.helpers.entity", DeviceInfo=DeviceInfo)
_make_module("homeassistant.helpers.entity_platform", AddEntitiesCallback=MagicMock)
_make_module("homeassistant.helpers", update_coordinator=sys.modules["homeassistant.helpers.update_coordinator"])
_make_module(
    "homeassistant.config_entries",
    ConfigEntry=MagicMock,
    current_entry=MagicMock(),
)
_make_module("homeassistant.core", HomeAssistant=MagicMock)
_make_module("homeassistant.helpers.aiohttp_client", async_get_clientsession=MagicMock())

# --- homeassistant (top-level) ---
_make_module("homeassistant")
