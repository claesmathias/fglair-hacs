"""DataUpdateCoordinator for the FGLair integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FglAirApi
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class FglAirCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll all registered devices and cache their property dicts."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: FglAirApi,
        devices: list[dict],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        # Keyed by DSN for fast lookup
        self.devices: dict[str, dict] = {
            d["device"]["dsn"]: d["device"] for d in devices
        }

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        errors: list[str] = []

        for dsn in self.devices:
            try:
                result[dsn] = await self.api.get_properties_with_retry(dsn)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Failed to update %s: %s", dsn, exc)
                errors.append(dsn)
                # Keep the last known state if we have one
                if self.data and dsn in self.data:
                    result[dsn] = self.data[dsn]

        if errors and not result:
            raise UpdateFailed(f"Could not update any devices: {errors}")

        return result
