"""Tests for FglAirApi credential building and retry logic."""
import asyncio
import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.fujitsu_airstage.api import _build_credentials, FglAirApi


class TestBuildCredentials:
    def test_fglair_eu_app_id(self):
        app_id, _ = _build_credentials("fglair-eu")
        assert app_id == "FGLair-eu-id"

    def test_fglair_eu_app_secret_format(self):
        _, app_secret = _build_credentials("fglair-eu")
        # Must start with prefix and use URL-safe base64 (no + / =)
        assert app_secret.startswith("FGLair-eu-")
        assert "+" not in app_secret
        assert "/" not in app_secret
        assert "=" not in app_secret

    def test_fglair_us_app_id(self):
        app_id, _ = _build_credentials("fglair-us")
        assert app_id == "CJIOSP-id"

    def test_hisense_eu_app_id(self):
        app_id, _ = _build_credentials("hisense-eu")
        assert app_id == "Hisense-id"

    def test_hisense_us_app_id(self):
        app_id, _ = _build_credentials("hisense-us")
        assert app_id == "APP1-id"

    def test_different_apps_produce_different_secrets(self):
        _, eu_secret = _build_credentials("fglair-eu")
        _, us_secret = _build_credentials("fglair-us")
        assert eu_secret != us_secret


class TestApiRetry:
    """Verify the _request method retries on transient errors."""

    def _make_api(self) -> FglAirApi:
        session = MagicMock(spec=aiohttp.ClientSession)
        return FglAirApi("user@test.com", "pass", "fglair-eu", session)

    def _fail_cm(self, exc: Exception) -> MagicMock:
        """Async context manager whose __aenter__ raises exc."""
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(side_effect=exc)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    def _success_cm(self, data: dict) -> MagicMock:
        """Async context manager that yields a successful response."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = AsyncMock(return_value=data)
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=resp)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self):
        api = self._make_api()
        err = aiohttp.ClientConnectionError("connection reset")
        # First two attempts fail, third succeeds
        api._session.request = MagicMock(side_effect=[
            self._fail_cm(err),
            self._fail_cm(err),
            self._success_cm({"ok": True}),
        ])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await api._request("GET", "https://example.com/test")
        assert result == {"ok": True}
        assert api._session.request.call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        api = self._make_api()
        err = aiohttp.ClientConnectionError("always down")
        api._session.request = MagicMock(side_effect=[
            self._fail_cm(err),
            self._fail_cm(err),
            self._fail_cm(err),
        ])
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(aiohttp.ClientConnectionError):
                await api._request("GET", "https://example.com/test")

    @pytest.mark.asyncio
    async def test_does_not_retry_on_http_4xx(self):
        api = self._make_api()
        resp = MagicMock()
        resp.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(MagicMock(), (), status=400)
        )
        resp.json = AsyncMock(return_value={})
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=resp)
        cm.__aexit__ = AsyncMock(return_value=False)
        api._session.request = MagicMock(return_value=cm)
        with pytest.raises(aiohttp.ClientResponseError):
            await api._request("GET", "https://example.com/test")
        assert api._session.request.call_count == 1  # no retry on 4xx

    @pytest.mark.asyncio
    async def test_get_device_properties_returns_name_value_dict(self):
        api = self._make_api()
        api._access_token = "tok"
        raw = [
            {"property": {"name": "operation_mode", "value": 3, "updated_at": "2026-06-16T12:00:00Z"}},
            {"property": {"name": "display_temperature", "value": 7100, "updated_at": "2026-06-16T11:55:00Z"}},
        ]
        api._request = AsyncMock(return_value=raw)
        result = await api.get_device_properties("AC000W123")
        assert result["operation_mode"] == 3
        assert result["display_temperature"] == 7100
        assert result["__ts_operation_mode"] == "2026-06-16T12:00:00Z"
        assert result["__ts_display_temperature"] == "2026-06-16T11:55:00Z"
