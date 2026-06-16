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
        # Keyed by DSN for fast lookup; refreshed on every poll
        self.devices: dict[str, dict] = {
            d["device"]["dsn"]: d["device"] for d in devices
        }

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        errors: list[str] = []

        # Refresh connection_status for all devices
        try:
            fresh = await self.api.get_devices()
            for d in fresh:
                dev = d["device"]
                dsn = dev["dsn"]
                if dsn in self.devices:
                    self.devices[dsn] = dev
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Could not refresh device list: %s", exc)

        for dsn in self.devices:
            connection_status = self.devices[dsn].get("connection_status", "Online")
            if connection_status != "Online":
                _LOGGER.debug("Device %s is offline (status: %s)", dsn, connection_status)
                result[dsn] = {"__online": False}
                continue

            try:
                props = await self.api.get_properties_with_retry(dsn)
                props["__online"] = True
                result[dsn] = props

                # FGL devices: trigger a fresh sensor read from the AC unit by
                # writing get_prop=1. The AC responds by pushing a new
                # display_temperature to the cloud; the next poll picks it up.
                if "get_prop" in props:
                    try:
                        await self.api.set_device_property(dsn, "get_prop", 1)
                    except Exception:  # noqa: BLE001
                        pass  # Non-critical; next poll reads whatever the cloud has

            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Failed to update %s: %s", dsn, exc)
                errors.append(dsn)
                # Keep the last known state if we have one
                if self.data and dsn in self.data:
                    result[dsn] = self.data[dsn]

        if errors and not result:
            raise UpdateFailed(f"Could not update any devices: {errors}")

        return result
