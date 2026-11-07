"""Tests for FglAirCoordinator offline detection and get_prop refresh."""
import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.fujitsu_airstage.coordinator import FglAirCoordinator


def _make_coordinator(devices: list[dict]) -> tuple[FglAirCoordinator, MagicMock]:
    api = MagicMock()
    api.get_devices = AsyncMock(return_value=devices)
    api.get_properties_with_retry = AsyncMock(return_value={
        "operation_mode": 3,
        "display_temperature": 7100,
        "get_prop": 0,
        "__online": True,
    })
    api.set_device_property = AsyncMock()
    hass = MagicMock()
    coord = FglAirCoordinator(hass, api, devices)
    return coord, api


def _online_device(dsn: str) -> dict:
    return {"device": {"dsn": dsn, "connection_status": "Online", "oem_model": "AP-WD1E"}}


def _offline_device(dsn: str) -> dict:
    return {"device": {"dsn": dsn, "connection_status": "Offline", "oem_model": "AP-WD1E"}}


class TestCoordinatorOfflineDetection:
    @pytest.mark.asyncio
    async def test_online_device_returns_props(self):
        devices = [_online_device("DSN001")]
        coord, api = _make_coordinator(devices)
        result = await coord._async_update_data()
        assert result["DSN001"]["__online"] is True
        assert result["DSN001"]["operation_mode"] == 3

    @pytest.mark.asyncio
    async def test_offline_device_marked_not_online(self):
        devices = [_online_device("DSN001")]
        coord, api = _make_coordinator(devices)
        # Simulate device going offline before the poll
        api.get_devices = AsyncMock(return_value=[_offline_device("DSN001")])
        result = await coord._async_update_data()
        assert result["DSN001"]["__online"] is False
        api.get_properties_with_retry.assert_not_called()

    @pytest.mark.asyncio
    async def test_offline_device_skips_property_fetch(self):
        devices = [_offline_device("DSN001")]
        coord, api = _make_coordinator(devices)
        await coord._async_update_data()
        api.get_properties_with_retry.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_devices_online_and_offline(self):
        devices = [_online_device("DSN001"), _online_device("DSN002")]
        coord, api = _make_coordinator(devices)
        api.get_devices = AsyncMock(return_value=[
            _online_device("DSN001"),
            _offline_device("DSN002"),
        ])
        result = await coord._async_update_data()
        assert result["DSN001"]["__online"] is True
        assert result["DSN002"]["__online"] is False


class TestCoordinatorGetPropRefresh:
    @pytest.mark.asyncio
    async def test_get_prop_written_for_fgl_device(self):
        devices = [_online_device("DSN001")]
        coord, api = _make_coordinator(devices)
        await coord._async_update_data()
        api.set_device_property.assert_called_once_with("DSN001", "get_prop", 1)

    @pytest.mark.asyncio
    async def test_get_prop_not_written_for_ac_device(self):
        devices = [_online_device("DSN001")]
        coord, api = _make_coordinator(devices)
        # AC devices don't have get_prop in their properties
        api.get_properties_with_retry = AsyncMock(return_value={
            "t_power": 1,
            "t_work_mode": 2,
            "f_temp_in": 72.0,
            "__online": True,
        })
        await coord._async_update_data()
        api.set_device_property.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_prop_failure_does_not_raise(self):
        devices = [_online_device("DSN001")]
        coord, api = _make_coordinator(devices)
        api.set_device_property = AsyncMock(side_effect=Exception("network error"))
        # Should not raise — get_prop is non-critical
        result = await coord._async_update_data()
        assert result["DSN001"]["__online"] is True

    @pytest.mark.asyncio
    async def test_failed_property_fetch_falls_back_to_last_known(self):
        devices = [_online_device("DSN001")]
        coord, api = _make_coordinator(devices)
        # Prime coordinator with prior data
        coord.data = {"DSN001": {"operation_mode": 2, "__online": True}}
        api.get_properties_with_retry = AsyncMock(side_effect=Exception("timeout"))
        result = await coord._async_update_data()
        assert result["DSN001"]["operation_mode"] == 2


class TestCoordinatorTemplateB:
    @pytest.mark.asyncio
    async def test_get_prop_not_written_for_template_b(self):
        # Template B (AP-WB*) units have no room temperature in the FGLair app
        devices = [{"device": {"dsn": "DSN001", "connection_status": "Online", "oem_model": "AP-WB2E"}}]
        coord, api = _make_coordinator(devices)
        await coord._async_update_data()
        api.set_device_property.assert_not_called()
