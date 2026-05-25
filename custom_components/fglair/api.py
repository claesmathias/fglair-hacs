"""Ayla Networks cloud API client for FGLair / Hisense AC units."""
from __future__ import annotations

import base64
import logging
from typing import Any

import aiohttp

from .const import AYLA_USER_SERVERS, AYLA_DEVICES_SERVERS, APP_CONFIGS

_LOGGER = logging.getLogger(__name__)

_USER_AGENT = "Dalvik/2.1.0 (Linux; U; Android 9.0; SM-G850F Build/LRX22G)"


def _build_credentials(app_key: str) -> tuple[str, str]:
    """Return (app_id, app_secret) for the given app key."""
    cfg = APP_CONFIGS[app_key]
    prefix = cfg["prefix"]
    secret_b64 = (
        base64.b64encode(cfg["secret"])
        .decode("utf-8")
        .rstrip("=")
        .replace("+", "-")
        .replace("/", "_")
    )
    return f"{prefix}-id", f"{prefix}-{secret_b64}"


class FglAirApi:
    """Async client wrapping the Ayla Networks REST API."""

    def __init__(
        self,
        username: str,
        password: str,
        app_key: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._username = username
        self._password = password
        self._app_key = app_key
        self._session = session
        self._access_token: str | None = None

        cfg = APP_CONFIGS[app_key]
        region = cfg["region"]
        self._user_server = AYLA_USER_SERVERS[region]
        self._devices_server = AYLA_DEVICES_SERVERS[region]
        self._app_id, self._app_secret = _build_credentials(app_key)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        """Sign in and store the access token."""
        payload = {
            "user": {
                "email": self._username,
                "password": self._password,
                "application": {
                    "app_id": self._app_id,
                    "app_secret": self._app_secret,
                },
            }
        }
        headers = {
            "Accept": "application/json",
            "Connection": "Keep-Alive",
            "Authorization": "none",
            "Content-Type": "application/json",
            "User-Agent": _USER_AGENT,
            "Host": self._user_server,
            "Accept-Encoding": "gzip",
        }
        async with self._session.post(
            f"https://{self._user_server}/users/sign_in.json",
            json=payload,
            headers=headers,
            ssl=False,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
            self._access_token = data["access_token"]
            _LOGGER.debug("FGLair authentication successful")

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Connection": "Keep-Alive",
            "Authorization": f"auth_token {self._access_token}",
            "User-Agent": _USER_AGENT,
            "Host": self._devices_server,
            "Accept-Encoding": "gzip",
        }

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    async def get_devices(self) -> list[dict]:
        """Return a list of device dicts from the Ayla devices API."""
        async with self._session.get(
            f"https://{self._devices_server}/apiv1/devices.json",
            headers=self._headers(),
            ssl=False,
        ) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)

    # ------------------------------------------------------------------
    # Property access
    # ------------------------------------------------------------------

    async def get_device_properties(self, dsn: str) -> dict[str, Any]:
        """Return {property_name: value} for a device."""
        async with self._session.get(
            f"https://{self._devices_server}/apiv1/dsns/{dsn}/properties.json",
            headers=self._headers(),
            ssl=False,
        ) as resp:
            resp.raise_for_status()
            raw = await resp.json(content_type=None)
            return {item["property"]["name"]: item["property"]["value"] for item in raw}

    async def set_device_property(self, dsn: str, name: str, value: Any) -> None:
        """Write a single property datapoint."""
        url = (
            f"https://{self._devices_server}"
            f"/apiv1/dsns/{dsn}/properties/{name}/datapoints.json"
        )
        async with self._session.post(
            url,
            json={"datapoint": {"value": value}},
            headers=self._headers(),
            ssl=False,
        ) as resp:
            resp.raise_for_status()
            _LOGGER.debug("Set %s.%s = %r", dsn, name, value)

    # ------------------------------------------------------------------
    # Token-aware wrapper: re-auth on 401 then retry once
    # ------------------------------------------------------------------

    async def get_properties_with_retry(self, dsn: str) -> dict[str, Any]:
        try:
            return await self.get_device_properties(dsn)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 401:
                _LOGGER.debug("Token expired, re-authenticating")
                await self.authenticate()
                return await self.get_device_properties(dsn)
            raise

    async def set_property_with_retry(self, dsn: str, name: str, value: Any) -> None:
        try:
            await self.set_device_property(dsn, name, value)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 401:
                _LOGGER.debug("Token expired, re-authenticating")
                await self.authenticate()
                await self.set_device_property(dsn, name, value)
            raise
