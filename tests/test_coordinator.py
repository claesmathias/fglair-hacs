"""Tests for FglAirCoordinator offline detection and get_prop refresh."""
import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.fujitsu_airstage.coordinator import FglAirCoordinator


def _make_coordinator(devices: list[dict]) -> tuple[FglAirCoordinator, MagicMock]:
    api = MagicMock()
    api.get_devices_with_retry = AsyncMock(return_value=devices)
    api.get_properties_with_retry = AsyncMock(return_value={
        "operation_mode": 3,
        "display_temperature": 7100,
        "get_prop": 0,
        "__online": True,
    })
    api.set_device_property = AsyncMock()
    hass = MagicMock()
    coord = FglAirCoordinator(hass, api, devices, "ENTRY1")
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
        api.get_devices_with_retry = AsyncMock(return_value=[_offline_device("DSN001")])
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
        api.get_devices_with_retry = AsyncMock(return_value=[
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


# ---------------------------------------------------------------------------
# Repairs issues and auth failures
# ---------------------------------------------------------------------------

import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed


@pytest.fixture(autouse=True)
def _reset_issue_registry():
    ir.async_create_issue.reset_mock()
    ir.async_delete_issue.reset_mock()


def _created_issue_ids():
    return [c.args[2] for c in ir.async_create_issue.call_args_list]


def _deleted_issue_ids():
    return [c.args[2] for c in ir.async_delete_issue.call_args_list]


def _cloud_down(api):
    err = aiohttp.ClientConnectionError("Cannot connect to host")
    api.get_devices_with_retry = AsyncMock(side_effect=err)
    api.get_properties_with_retry = AsyncMock(side_effect=err)


class TestDeviceOfflineIssue:
    @pytest.mark.asyncio
    async def test_issue_created_when_device_goes_offline(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        api.get_devices_with_retry = AsyncMock(return_value=[_offline_device("DSN001")])
        await coord._async_update_data()
        assert _created_issue_ids() == ["device_offline_DSN001"]
        kwargs = ir.async_create_issue.call_args.kwargs
        assert kwargs["translation_key"] == "device_offline"
        assert kwargs["translation_placeholders"]["dsn"] == "DSN001"

    @pytest.mark.asyncio
    async def test_issue_created_only_once(self):
        coord, api = _make_coordinator([_offline_device("DSN001")])
        api.get_devices_with_retry = AsyncMock(return_value=[_offline_device("DSN001")])
        await coord._async_update_data()
        await coord._async_update_data()
        assert ir.async_create_issue.call_count == 1

    @pytest.mark.asyncio
    async def test_issue_removed_when_device_back_online(self):
        coord, api = _make_coordinator([_offline_device("DSN001")])
        api.get_devices_with_retry = AsyncMock(return_value=[_offline_device("DSN001")])
        await coord._async_update_data()
        api.get_devices_with_retry = AsyncMock(return_value=[_online_device("DSN001")])
        await coord._async_update_data()
        assert _deleted_issue_ids() == ["device_offline_DSN001"]

    @pytest.mark.asyncio
    async def test_no_issue_for_online_device(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        await coord._async_update_data()
        ir.async_create_issue.assert_not_called()
        ir.async_delete_issue.assert_not_called()


class TestCloudUnreachable:
    @pytest.mark.asyncio
    async def test_first_refresh_failure_raises(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        _cloud_down(api)
        with pytest.raises(UpdateFailed):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_short_blip_keeps_last_state_without_issue(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        coord.data = {"DSN001": {"operation_mode": 2, "__online": True}}
        _cloud_down(api)
        result = await coord._async_update_data()
        assert result["DSN001"]["operation_mode"] == 2
        ir.async_create_issue.assert_not_called()

    @pytest.mark.asyncio
    async def test_sustained_outage_raises_and_creates_issue(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        coord.data = {"DSN001": {"operation_mode": 2, "__online": True}}
        _cloud_down(api)
        await coord._async_update_data()
        await coord._async_update_data()
        with pytest.raises(UpdateFailed):
            await coord._async_update_data()
        assert _created_issue_ids() == ["cloud_unreachable_ENTRY1"]
        kwargs = ir.async_create_issue.call_args.kwargs
        assert kwargs["translation_key"] == "cloud_unreachable"
        assert kwargs["severity"] == ir.IssueSeverity.ERROR
        # A device's cached status must not raise an offline issue while the cloud is down
        assert "device_offline_DSN001" not in _created_issue_ids()

    @pytest.mark.asyncio
    async def test_issue_removed_when_cloud_returns(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        coord.data = {"DSN001": {"operation_mode": 2, "__online": True}}
        good_devices = api.get_devices_with_retry
        good_props = api.get_properties_with_retry
        _cloud_down(api)
        for _ in range(3):
            try:
                await coord._async_update_data()
            except UpdateFailed:
                pass
        api.get_devices_with_retry = good_devices
        api.get_properties_with_retry = good_props
        result = await coord._async_update_data()
        assert result["DSN001"]["__online"] is True
        assert "cloud_unreachable_ENTRY1" in _deleted_issue_ids()

    @pytest.mark.asyncio
    async def test_clear_issues_removes_everything(self):
        coord, api = _make_coordinator([_offline_device("DSN001")])
        api.get_devices_with_retry = AsyncMock(return_value=[_offline_device("DSN001")])
        await coord._async_update_data()
        coord.clear_issues()
        assert set(_deleted_issue_ids()) == {"cloud_unreachable_ENTRY1", "device_offline_DSN001"}


class TestAuthFailure:
    @pytest.mark.asyncio
    async def test_rejected_credentials_on_device_list_start_reauth(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        api.get_devices_with_retry = AsyncMock(
            side_effect=aiohttp.ClientResponseError(MagicMock(), (), status=401)
        )
        with pytest.raises(ConfigEntryAuthFailed):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_rejected_credentials_on_properties_start_reauth(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        api.get_properties_with_retry = AsyncMock(
            side_effect=aiohttp.ClientResponseError(MagicMock(), (), status=403)
        )
        with pytest.raises(ConfigEntryAuthFailed):
            await coord._async_update_data()

    @pytest.mark.asyncio
    async def test_server_error_is_not_auth_failure(self):
        coord, api = _make_coordinator([_online_device("DSN001")])
        coord.data = {"DSN001": {"operation_mode": 2, "__online": True}}
        api.get_properties_with_retry = AsyncMock(
            side_effect=aiohttp.ClientResponseError(MagicMock(), (), status=500)
        )
        result = await coord._async_update_data()
        assert result["DSN001"]["operation_mode"] == 2
