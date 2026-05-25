"""Climate platform for the FGLair integration."""
from __future__ import annotations

import logging
import math
import re
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    FGL_MODEL_RE,
    FGLB_MODEL_RE,
    FGL_TEMP_SCALE,  # used in _adjust_to_celsius / _celsius_to_adjust
    FGL_MODE_TO_HA,
    HA_MODE_TO_FGL,
    FGL_FAN_TO_HA,
    HA_FAN_TO_FGL,
    AC_MODE_TO_HA,
    HA_MODE_TO_AC,
    AC_FAN_TO_HA,
    HA_FAN_TO_AC,
    APP_CONFIGS,
    CONF_APP,
)
from .coordinator import FglAirCoordinator

_LOGGER = logging.getLogger(__name__)

_FGL_RE = re.compile(FGL_MODEL_RE)
_FGLB_RE = re.compile(FGLB_MODEL_RE)


def _device_type(model: str) -> str:
    if _FGL_RE.fullmatch(model):
        return "fgl"
    if _FGLB_RE.fullmatch(model):
        return "fglb"
    return "ac"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FglAirCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    celsius = APP_CONFIGS[entry.data[CONF_APP]]["celsius"]

    entities = [
        FglAirClimate(coordinator, api, dsn, device_info, celsius)
        for dsn, device_info in coordinator.devices.items()
    ]
    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _adjust_to_celsius(raw: int | None) -> float | None:
    """adjust_temperature: stored as tenths of °C (210 = 21.0 °C)."""
    if raw is None:
        return None
    return round(raw / FGL_TEMP_SCALE, 1)


def _celsius_to_adjust(celsius: float) -> int:
    return round(celsius * FGL_TEMP_SCALE)


def _display_to_celsius(raw: int | None) -> float | None:
    """display_temperature: lookup-table encoded value from the FGLair app.

    The table maps display integers to 0.5 °C steps via:
        celsius = floor((display - 5000) / 50) * 0.5
    (derived from the TEMPERATURES array in the FGLair 3.4.2 APK build.js)
    """
    if raw is None:
        return None
    return math.floor((raw - 5000) / 50) * 0.5


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

class FglAirClimate(CoordinatorEntity[FglAirCoordinator], ClimateEntity):
    """Single AC unit exposed as a HA climate entity."""

    _attr_has_entity_name = True
    _attr_name = None  # device name is used as entity name

    def __init__(
        self,
        coordinator: FglAirCoordinator,
        api,
        dsn: str,
        device_info: dict,
        celsius: bool,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._dsn = dsn
        self._device_info = device_info
        self._celsius = celsius
        self._dtype = _device_type(device_info.get("oem_model", ""))

        self._attr_unique_id = dsn
        self._attr_temperature_unit = (
            UnitOfTemperature.CELSIUS if celsius else UnitOfTemperature.FAHRENHEIT
        )

        # Capabilities differ between FGL, FGLB, and AC devices
        if self._dtype in ("fgl", "fglb"):
            self._attr_hvac_modes = [
                HVACMode.OFF,
                HVACMode.AUTO,
                HVACMode.COOL,
                HVACMode.HEAT,
                HVACMode.DRY,
                HVACMode.FAN_ONLY,
            ]
            self._attr_fan_modes = ["auto", "quiet", "low", "medium", "high"]
            self._attr_min_temp = 16.0
            self._attr_max_temp = 30.0
            self._attr_target_temp_step = 1.0
            features = (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.TURN_ON
                | ClimateEntityFeature.TURN_OFF
            )
            if self._dtype == "fgl":
                self._attr_swing_modes = ["on", "off"]
                features |= ClimateEntityFeature.SWING_MODE
            self._attr_supported_features = features
        else:
            # Generic AC device (Hisense non-FGL)
            self._attr_hvac_modes = [
                HVACMode.OFF,
                HVACMode.AUTO,
                HVACMode.COOL,
                HVACMode.HEAT,
                HVACMode.DRY,
                HVACMode.FAN_ONLY,
            ]
            self._attr_fan_modes = ["auto", "lower", "low", "medium", "high", "higher"]
            self._attr_min_temp = 16.0
            self._attr_max_temp = 30.0
            self._attr_target_temp_step = 1.0
            self._attr_supported_features = (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.SWING_MODE
                | ClimateEntityFeature.TURN_ON
                | ClimateEntityFeature.TURN_OFF
            )
            self._attr_swing_modes = ["on", "off"]

    # ------------------------------------------------------------------
    # Device registry
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        info = self._device_info
        name = (
            info.get("friendly_name")
            or info.get("product_name")
            or self._dsn
        )
        return DeviceInfo(
            identifiers={(DOMAIN, self._dsn)},
            name=name,
            manufacturer="Hisense / Fujitsu",
            model=info.get("oem_model"),
            sw_version=info.get("sw_version"),
        )

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    @property
    def _props(self) -> dict:
        if self.coordinator.data and self._dsn in self.coordinator.data:
            return self.coordinator.data[self._dsn]
        return {}

    def _get(self, key: str):
        return self._props.get(key)

    # ------------------------------------------------------------------
    # FGL state
    # ------------------------------------------------------------------

    def _fgl_hvac_mode(self) -> HVACMode:
        raw = self._get("operation_mode")
        if raw is None:
            return HVACMode.OFF
        mode_str = FGL_MODE_TO_HA.get(int(raw), "off")
        return HVACMode(mode_str)

    def _fgl_current_temp(self) -> float | None:
        return _display_to_celsius(self._get("display_temperature"))

    def _fgl_target_temp(self) -> float | None:
        return _adjust_to_celsius(self._get("adjust_temperature"))

    def _fgl_fan_mode(self) -> str | None:
        raw = self._get("fan_speed")
        if raw is None:
            return None
        return FGL_FAN_TO_HA.get(int(raw))

    def _fgl_swing_mode(self) -> str | None:
        raw = self._get("af_vertical_swing")
        if raw is None:
            return None
        return "on" if int(raw) else "off"

    # ------------------------------------------------------------------
    # AC state
    # ------------------------------------------------------------------

    def _ac_hvac_mode(self) -> HVACMode:
        power_raw = self._get("t_power")
        if power_raw is not None and int(power_raw) == 0:
            return HVACMode.OFF
        raw = self._get("t_work_mode")
        if raw is None:
            return HVACMode.OFF
        mode_str = AC_MODE_TO_HA.get(int(raw), "auto")
        return HVACMode(mode_str)

    def _ac_current_temp(self) -> float | None:
        raw = self._get("f_temp_in")
        if raw is None:
            return None
        val = float(raw)
        # f_temp_in is always Fahrenheit; convert if the app uses Celsius
        if self._celsius:
            val = round((val - 32) * 5 / 9, 1)
        return val

    def _ac_target_temp(self) -> float | None:
        raw = self._get("t_temp")
        if raw is None:
            return None
        val = float(raw)
        if self._celsius:
            val = round((val - 32) * 5 / 9, 1)
        return val

    def _ac_fan_mode(self) -> str | None:
        raw = self._get("t_fan_speed")
        if raw is None:
            return None
        return AC_FAN_TO_HA.get(int(raw))

    def _ac_swing_mode(self) -> str | None:
        raw = self._get("t_fan_power")
        if raw is None:
            return None
        return "on" if int(raw) else "off"

    # ------------------------------------------------------------------
    # HA properties
    # ------------------------------------------------------------------

    @property
    def hvac_mode(self) -> HVACMode:
        if self._dtype in ("fgl", "fglb"):
            return self._fgl_hvac_mode()
        return self._ac_hvac_mode()

    @property
    def current_temperature(self) -> float | None:
        if self._dtype in ("fgl", "fglb"):
            return self._fgl_current_temp()
        return self._ac_current_temp()

    @property
    def target_temperature(self) -> float | None:
        if self._dtype in ("fgl", "fglb"):
            return self._fgl_target_temp()
        return self._ac_target_temp()

    @property
    def fan_mode(self) -> str | None:
        if self._dtype in ("fgl", "fglb"):
            return self._fgl_fan_mode()
        return self._ac_fan_mode()

    @property
    def swing_mode(self) -> str | None:
        if self._dtype == "fgl":
            return self._fgl_swing_mode()
        if self._dtype == "ac":
            return self._ac_swing_mode()
        return None

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if self._dtype in ("fgl", "fglb"):
            value = HA_MODE_TO_FGL[hvac_mode]
            await self._api.set_property_with_retry(self._dsn, "operation_mode", value)
        else:
            if hvac_mode == HVACMode.OFF:
                await self._api.set_property_with_retry(self._dsn, "t_power", 0)
            else:
                await self._api.set_property_with_retry(self._dsn, "t_power", 1)
                value = HA_MODE_TO_AC.get(hvac_mode, 4)
                await self._api.set_property_with_retry(self._dsn, "t_work_mode", value)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        if self._dtype in ("fgl", "fglb"):
            await self._api.set_property_with_retry(
                self._dsn, "adjust_temperature", _celsius_to_adjust(temp)
            )
        else:
            if not self._celsius:
                # Convert Celsius → Fahrenheit for the API
                temp = round(temp * 9 / 5 + 32)
            await self._api.set_property_with_retry(self._dsn, "t_temp", int(temp))
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if self._dtype in ("fgl", "fglb"):
            value = HA_FAN_TO_FGL[fan_mode]
            await self._api.set_property_with_retry(self._dsn, "fan_speed", value)
        else:
            value = HA_FAN_TO_AC.get(fan_mode, 0)
            await self._api.set_property_with_retry(self._dsn, "t_fan_speed", value)
        await self.coordinator.async_request_refresh()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        value = 1 if swing_mode == "on" else 0
        if self._dtype == "fgl":
            await self._api.set_property_with_retry(self._dsn, "af_vertical_swing", value)
        else:
            await self._api.set_property_with_retry(self._dsn, "t_fan_power", value)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        if self._dtype in ("fgl", "fglb"):
            await self._api.set_property_with_retry(self._dsn, "operation_mode", 2)  # AUTO
        else:
            await self._api.set_property_with_retry(self._dsn, "t_power", 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        if self._dtype in ("fgl", "fglb"):
            await self._api.set_property_with_retry(self._dsn, "operation_mode", 0)
        else:
            await self._api.set_property_with_retry(self._dsn, "t_power", 0)
        await self.coordinator.async_request_refresh()
