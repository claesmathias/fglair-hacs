"""Tests for FglAirClimate entity state and command handling."""
import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import AsyncMock, MagicMock
from custom_components.fujitsu_airstage.climate import FglAirClimate
from custom_components.fujitsu_airstage.const import DOMAIN

# HomeAssistantError comes from our conftest stub
from homeassistant.exceptions import HomeAssistantError


def _make_entity(props: dict, oem_model: str = "AP-WD1E", celsius: bool = True) -> FglAirClimate:
    coordinator = MagicMock()
    coordinator.data = {"DSN001": props}
    api = MagicMock()
    api.set_property_with_retry = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    device_info = {"dsn": "DSN001", "oem_model": oem_model, "friendly_name": "Test AC"}
    entity = FglAirClimate(coordinator, api, "DSN001", device_info, celsius)
    return entity


class TestFglHvacMode:
    def test_off(self):
        e = _make_entity({"operation_mode": 0, "__online": True})
        assert e.hvac_mode.value == "off"

    def test_auto(self):
        e = _make_entity({"operation_mode": 2, "__online": True})
        assert e.hvac_mode.value == "auto"

    def test_cool(self):
        e = _make_entity({"operation_mode": 3, "__online": True})
        assert e.hvac_mode.value == "cool"

    def test_heat(self):
        e = _make_entity({"operation_mode": 6, "__online": True})
        assert e.hvac_mode.value == "heat"

    def test_dry(self):
        e = _make_entity({"operation_mode": 4, "__online": True})
        assert e.hvac_mode.value == "dry"

    def test_fan_only(self):
        e = _make_entity({"operation_mode": 5, "__online": True})
        assert e.hvac_mode.value == "fan_only"

    def test_none_returns_off(self):
        e = _make_entity({"__online": True})
        assert e.hvac_mode.value == "off"


class TestFglCurrentTemperature:
    def test_typical(self):
        # 7100 → floor((7100-5000)/50)*0.5 = 21.0
        e = _make_entity({"display_temperature": 7100, "__online": True})
        assert e.current_temperature == 21.0

    def test_none_when_missing(self):
        e = _make_entity({"__online": True})
        assert e.current_temperature is None


class TestFglTargetTemperature:
    def test_typical(self):
        # 210 → 21.0
        e = _make_entity({"adjust_temperature": 210, "__online": True})
        assert e.target_temperature == 21.0

    def test_none_when_missing(self):
        e = _make_entity({"__online": True})
        assert e.target_temperature is None


class TestAvailability:
    def test_online(self):
        e = _make_entity({"__online": True})
        assert e.available is True

    def test_offline(self):
        e = _make_entity({"__online": False})
        assert e.available is False

    def test_defaults_to_available_when_key_missing(self):
        e = _make_entity({})
        assert e.available is True


class TestOfflineCommandGuard:
    @pytest.mark.asyncio
    async def test_set_hvac_mode_raises_when_offline(self):
        e = _make_entity({"__online": False})
        from homeassistant.components.climate import HVACMode
        with pytest.raises(HomeAssistantError):
            await e.async_set_hvac_mode(HVACMode.COOL)

    @pytest.mark.asyncio
    async def test_set_temperature_raises_when_offline(self):
        e = _make_entity({"__online": False})
        with pytest.raises(HomeAssistantError):
            await e.async_set_temperature(temperature=22.0)

    @pytest.mark.asyncio
    async def test_set_fan_mode_raises_when_offline(self):
        e = _make_entity({"__online": False})
        with pytest.raises(HomeAssistantError):
            await e.async_set_fan_mode("auto")

    @pytest.mark.asyncio
    async def test_turn_on_raises_when_offline(self):
        e = _make_entity({"__online": False})
        with pytest.raises(HomeAssistantError):
            await e.async_turn_on()

    @pytest.mark.asyncio
    async def test_turn_off_raises_when_offline(self):
        e = _make_entity({"__online": False})
        with pytest.raises(HomeAssistantError):
            await e.async_turn_off()


class TestTurnOnSendsCorrectValue:
    @pytest.mark.asyncio
    async def test_fgl_turn_on_sends_operation_mode_1(self):
        e = _make_entity({"__online": True})
        await e.async_turn_on()
        e._api.set_property_with_retry.assert_awaited_once_with("DSN001", "operation_mode", 1)

    @pytest.mark.asyncio
    async def test_fgl_turn_off_sends_operation_mode_0(self):
        e = _make_entity({"__online": True})
        await e.async_turn_off()
        e._api.set_property_with_retry.assert_awaited_once_with("DSN001", "operation_mode", 0)


class TestTemperatureLastUpdatedAttribute:
    def test_exposes_timestamp_for_fgl(self):
        e = _make_entity({
            "display_temperature": 7100,
            "__ts_display_temperature": "2026-06-16T12:00:00Z",
            "__online": True,
        })
        attrs = e.extra_state_attributes
        assert attrs["temperature_last_updated"] == "2026-06-16T12:00:00Z"

    def test_empty_when_no_timestamp(self):
        e = _make_entity({"display_temperature": 7100, "__online": True})
        assert e.extra_state_attributes == {}


class TestFglValueOneIsOff:
    def test_operation_mode_1_reads_as_off(self):
        e = _make_entity({"operation_mode": 1, "__online": True})
        assert e.hvac_mode.value == "off"


class TestTemperatureStepAndRange:
    def test_template_a_f_half_degree_step(self):
        assert _make_entity({}, oem_model="AP-WD1E")._attr_target_temp_step == 0.5
        assert _make_entity({}, oem_model="AP-WF2E")._attr_target_temp_step == 0.5

    def test_template_b_whole_degree_step(self):
        assert _make_entity({}, oem_model="AP-WB1E")._attr_target_temp_step == 1.0

    def test_min_temp_heat_16(self):
        assert _make_entity({"operation_mode": 6}).min_temp == 16.0

    def test_min_temp_cool_18(self):
        assert _make_entity({"operation_mode": 3}).min_temp == 18.0

    def test_max_temp_30(self):
        assert _make_entity({})._attr_max_temp == 30.0

    def test_fgl_unit_always_celsius(self):
        # adjust_temperature is °C×10 even in the US (Fahrenheit) app
        from homeassistant.const import UnitOfTemperature
        e = _make_entity({}, celsius=False)
        assert e._attr_temperature_unit == UnitOfTemperature.CELSIUS

    @pytest.mark.asyncio
    async def test_set_temperature_half_degree(self):
        e = _make_entity({"__online": True})
        await e.async_set_temperature(temperature=21.5)
        e._api.set_property_with_retry.assert_awaited_once_with("DSN001", "adjust_temperature", 215)

    @pytest.mark.asyncio
    async def test_set_temperature_template_b_snaps_to_whole_degree(self):
        e = _make_entity({"__online": True}, oem_model="AP-WB1E")
        await e.async_set_temperature(temperature=21.4)
        e._api.set_property_with_retry.assert_awaited_once_with("DSN001", "adjust_temperature", 210)


class TestTemplateB:
    def test_no_room_temperature(self):
        e = _make_entity({"display_temperature": 7100}, oem_model="AP-WB1E")
        assert e.current_temperature is None

    def test_swing_on_when_move_step_3(self):
        e = _make_entity({"af_vertical_move_step1": 3}, oem_model="AP-WB1E")
        assert e.swing_mode == "on"

    def test_swing_off_when_fixed_position(self):
        e = _make_entity({"af_vertical_move_step1": 1}, oem_model="AP-WB1E")
        assert e.swing_mode == "off"

    @pytest.mark.asyncio
    async def test_set_swing_on_writes_move_step_3(self):
        e = _make_entity({"__online": True}, oem_model="AP-WB1E")
        await e.async_set_swing_mode("on")
        e._api.set_property_with_retry.assert_awaited_once_with("DSN001", "af_vertical_move_step1", 3)

    @pytest.mark.asyncio
    async def test_set_swing_off_writes_move_step_0(self):
        e = _make_entity({"__online": True}, oem_model="AP-WB1E")
        await e.async_set_swing_mode("off")
        e._api.set_property_with_retry.assert_awaited_once_with("DSN001", "af_vertical_move_step1", 0)


class TestMinimumHeat:
    def test_target_is_10_in_minimum_heat(self):
        e = _make_entity({"operation_mode": 6, "min_heat": 1, "adjust_temperature": 240})
        assert e.target_temperature == 10.0
        assert e.extra_state_attributes["minimum_heat"] is True

    def test_normal_heat(self):
        e = _make_entity({"operation_mode": 6, "min_heat": 0, "adjust_temperature": 220})
        assert e.target_temperature == 22.0
        assert e.extra_state_attributes["minimum_heat"] is False

    @pytest.mark.asyncio
    async def test_heat_from_minimum_heat_writes_basic_setpoint(self):
        from homeassistant.components.climate import HVACMode
        e = _make_entity({"operation_mode": 6, "min_heat": 1, "__online": True})
        await e.async_set_hvac_mode(HVACMode.HEAT)
        e._api.set_property_with_retry.assert_awaited_once_with("DSN001", "adjust_temperature", 240)

    @pytest.mark.asyncio
    async def test_cool_from_minimum_heat_sets_mode(self):
        from homeassistant.components.climate import HVACMode
        e = _make_entity({"operation_mode": 6, "min_heat": 1, "__online": True})
        await e.async_set_hvac_mode(HVACMode.COOL)
        e._api.set_property_with_retry.assert_awaited_once_with("DSN001", "operation_mode", 3)


class TestDeviceCapabilities:
    # cool|dry|fan|heat|auto + all fan speeds + vertical swing
    FULL = 0b11111 | (0b11111 << 5) | (1 << 10)

    def test_all_modes_without_capabilities(self):
        e = _make_entity({})
        assert len(e.hvac_modes) == 6
        assert e.fan_modes == ["auto", "quiet", "low", "medium", "high"]

    def test_cool_only_unit(self):
        caps = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 5) | (1 << 6)  # cool, dry, fan; auto+high fan
        e = _make_entity({"device_capabilities": caps})
        assert [m.value for m in e.hvac_modes] == ["off", "cool", "dry", "fan_only"]
        assert e.fan_modes == ["auto", "high"]

    def test_swing_feature_follows_capability(self):
        from homeassistant.components.climate import ClimateEntityFeature
        with_swing = _make_entity({"device_capabilities": self.FULL})
        without = _make_entity({"device_capabilities": self.FULL & ~(1 << 10)})
        assert with_swing.supported_features & ClimateEntityFeature.SWING_MODE
        assert not without.supported_features & ClimateEntityFeature.SWING_MODE
