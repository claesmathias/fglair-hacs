"""Climate platform for the FGLair integration."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    FGL_TEMP_SCALE,
    FGL_TEMP_STEP,
    FGLB_TEMP_STEP,
    FGL_MIN_TEMP,
    FGL_MIN_TEMP_HEAT,
    FGL_MAX_TEMP,
    FGL_MIN_HEAT_TEMP,
    FGL_HEAT_BASIC_ADJUST,
    FGL_DISPLAY_MIN,
    FGL_DISPLAY_MAX,
    FGL_CAP_MODES,
    FGL_CAP_FANS,
    FGL_CAP_VERTICAL_SWING,
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
from .models import device_type as _device_type

_LOGGER = logging.getLogger(__name__)

# Full FGL capability lists, used until device_capabilities has been read
_FGL_ALL_HVAC_MODES = [
    HVACMode.OFF,
    HVACMode.AUTO,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
]
_FGL_ALL_FAN_MODES = ["auto", "quiet", "low", "medium", "high"]

_BASE_FEATURES = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
)

# Template B swing lives in af_vertical_move_step1: 3 = swing, 0 = fixed position
_FGLB_SWING_ON = 3
_FGLB_SWING_OFF = 0


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
    return round(int(raw) / FGL_TEMP_SCALE, 1)


def _celsius_to_adjust(celsius: float) -> int:
    return round(celsius * FGL_TEMP_SCALE)


def _display_to_celsius(raw: int | None) -> float | None:
    """display_temperature: lookup-table encoded value from the FGLair app.

    The TEMPERATURES table in the FGLair APK (temperatures.js) maps display
    values 4000..9500 in steps of 25 to 0.5 °C steps from -10 °C to 45 °C:
        celsius = trunc((display - 5000) / 50) * 0.5
    (truncation toward zero, so negative temperatures round up, e.g. 4025 → -9.5).
    Values outside the table are shown as unknown by the app.
    """
    if raw is None:
        return None
    raw = int(raw)
    if not FGL_DISPLAY_MIN <= raw <= FGL_DISPLAY_MAX:
        return None
    return math.trunc((raw - 5000) / 50) * 0.5


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

        if self._is_fgl:
            # FGL units always report °C×10, whatever unit the app displays;
            # HA converts to the user's preferred unit.
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
            self._attr_max_temp = FGL_MAX_TEMP
            self._attr_target_temp_step = (
                FGLB_TEMP_STEP if self._dtype == "fglb" else FGL_TEMP_STEP
            )
            self._attr_swing_modes = ["on", "off"]
        else:
            # Generic AC device (Hisense non-FGL)
            self._attr_temperature_unit = (
                UnitOfTemperature.CELSIUS if celsius else UnitOfTemperature.FAHRENHEIT
            )
            self._attr_hvac_modes = list(_FGL_ALL_HVAC_MODES)
            self._attr_fan_modes = ["auto", "lower", "low", "medium", "high", "higher"]
            self._attr_min_temp = 16.0
            self._attr_max_temp = 30.0
            self._attr_target_temp_step = 1.0
            self._attr_supported_features = _BASE_FEATURES | ClimateEntityFeature.SWING_MODE
            self._attr_swing_modes = ["on", "off"]

    @property
    def _is_fgl(self) -> bool:
        return self._dtype in ("fgl", "fglb")

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

    def _fgl_capabilities(self) -> int | None:
        """device_capabilities bitmask, or None if not (yet) known."""
        raw = self._get("device_capabilities")
        try:
            caps = int(raw)
        except (TypeError, ValueError):
            return None
        return caps or None

    def _fgl_min_heat(self) -> bool:
        raw = self._get("min_heat")
        try:
            return int(raw) == 1
        except (TypeError, ValueError):
            return False

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
        # The FGLair app hides room temperature for template B units
        if self._dtype == "fglb":
            return None
        return _display_to_celsius(self._get("display_temperature"))

    def _fgl_target_temp(self) -> float | None:
        if self._fgl_min_heat():
            return FGL_MIN_HEAT_TEMP
        return _adjust_to_celsius(self._get("adjust_temperature"))

    def _fgl_fan_mode(self) -> str | None:
        raw = self._get("fan_speed")
        if raw is None:
            return None
        return FGL_FAN_TO_HA.get(int(raw))

    def _fgl_swing_mode(self) -> str | None:
        if self._dtype == "fglb":
            raw = self._get("af_vertical_move_step1")
            if raw is None:
                return None
            return "on" if int(raw) == _FGLB_SWING_ON else "off"
        raw = self._get("af_vertical_swing")
        if raw is None:
            return None
        return "on" if int(raw) == 1 else "off"

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
    # HA capability properties (FGL: derived from device_capabilities)
    # ------------------------------------------------------------------

    @property
    def hvac_modes(self) -> list[HVACMode]:
        if not self._is_fgl:
            return self._attr_hvac_modes
        caps = self._fgl_capabilities()
        if caps is None:
            return list(_FGL_ALL_HVAC_MODES)
        return [HVACMode.OFF] + [
            mode for mode in _FGL_ALL_HVAC_MODES[1:]
            if caps & FGL_CAP_MODES[mode.value]
        ]

    @property
    def fan_modes(self) -> list[str] | None:
        if not self._is_fgl:
            return self._attr_fan_modes
        caps = self._fgl_capabilities()
        if caps is None:
            return list(_FGL_ALL_FAN_MODES)
        return [fan for fan in _FGL_ALL_FAN_MODES if caps & FGL_CAP_FANS[fan]]

    @property
    def supported_features(self) -> ClimateEntityFeature:
        if not self._is_fgl:
            return self._attr_supported_features
        features = _BASE_FEATURES
        caps = self._fgl_capabilities()
        if caps is None or caps & FGL_CAP_VERTICAL_SWING:
            features |= ClimateEntityFeature.SWING_MODE
        return features

    @property
    def min_temp(self) -> float:
        if not self._is_fgl:
            return self._attr_min_temp
        # Heat (and off, so a heat setpoint can be pre-set) allow 16 °C; other modes 18 °C
        if self.hvac_mode in (HVACMode.AUTO, HVACMode.COOL, HVACMode.DRY, HVACMode.FAN_ONLY):
            return FGL_MIN_TEMP
        return FGL_MIN_TEMP_HEAT

    # ------------------------------------------------------------------
    # HA state properties
    # ------------------------------------------------------------------

    @property
    def hvac_mode(self) -> HVACMode:
        if self._is_fgl:
            return self._fgl_hvac_mode()
        return self._ac_hvac_mode()

    @property
    def current_temperature(self) -> float | None:
        if self._is_fgl:
            return self._fgl_current_temp()
        return self._ac_current_temp()

    @property
    def target_temperature(self) -> float | None:
        if self._is_fgl:
            return self._fgl_target_temp()
        return self._ac_target_temp()

    @property
    def fan_mode(self) -> str | None:
        if self._is_fgl:
            return self._fgl_fan_mode()
        return self._ac_fan_mode()

    @property
    def swing_mode(self) -> str | None:
        if self._is_fgl:
            return self._fgl_swing_mode()
        return self._ac_swing_mode()

    @property
    def available(self) -> bool:
        return self._props.get("__online", True)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose indoor sensor freshness and Minimum Heat state."""
        attrs: dict[str, Any] = {}
        if self._is_fgl:
            if self._dtype == "fgl":
                ts = self._get("__ts_display_temperature")
                if ts is not None:
                    attrs["temperature_last_updated"] = ts
            if self._get("min_heat") is not None:
                attrs["minimum_heat"] = self._fgl_min_heat()
        else:
            ts = self._get("__ts_f_temp_in")
            if ts is not None:
                attrs["temperature_last_updated"] = ts
        return attrs

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _assert_online(self) -> None:
        if not self.available:
            raise HomeAssistantError(
                f"{self._dsn} is offline — command not sent to the AC unit"
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._assert_online()
        if self._is_fgl:
            if hvac_mode == HVACMode.HEAT and self._fgl_min_heat():
                # Minimum Heat → Heat: the app leaves Minimum Heat by writing the
                # basic heat setpoint (24 °C); operation_mode is already "heat".
                await self._api.set_property_with_retry(
                    self._dsn, "adjust_temperature", FGL_HEAT_BASIC_ADJUST
                )
            else:
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
        self._assert_online()
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        if self._is_fgl:
            # Snap to the unit's step (0.5 °C, or 1 °C for template B)
            step = self._attr_target_temp_step
            temp = round(temp / step) * step
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
        self._assert_online()
        if self._is_fgl:
            value = HA_FAN_TO_FGL[fan_mode]
            await self._api.set_property_with_retry(self._dsn, "fan_speed", value)
        else:
            value = HA_FAN_TO_AC.get(fan_mode, 0)
            await self._api.set_property_with_retry(self._dsn, "t_fan_speed", value)
        await self.coordinator.async_request_refresh()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        self._assert_online()
        on = swing_mode == "on"
        if self._dtype == "fglb":
            await self._api.set_property_with_retry(
                self._dsn,
                "af_vertical_move_step1",
                _FGLB_SWING_ON if on else _FGLB_SWING_OFF,
            )
        elif self._dtype == "fgl":
            await self._api.set_property_with_retry(
                self._dsn, "af_vertical_swing", 1 if on else 0
            )
        else:
            await self._api.set_property_with_retry(self._dsn, "t_fan_power", 1 if on else 0)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        self._assert_online()
        if self._is_fgl:
            # App sends 1 ("ON" wake command); device transitions to last-used mode on its own
            await self._api.set_property_with_retry(self._dsn, "operation_mode", 1)
        else:
            await self._api.set_property_with_retry(self._dsn, "t_power", 1)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        self._assert_online()
        if self._is_fgl:
            await self._api.set_property_with_retry(self._dsn, "operation_mode", 0)
        else:
            await self._api.set_property_with_retry(self._dsn, "t_power", 0)
        await self.coordinator.async_request_refresh()
