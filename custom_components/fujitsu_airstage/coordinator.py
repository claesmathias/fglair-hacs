"""DataUpdateCoordinator for the FGLair integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FglAirApi, is_auth_error
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CLOUD_FAILURE_THRESHOLD
from .models import device_type

_LOGGER = logging.getLogger(__name__)


def cloud_issue_id(entry_id: str) -> str:
    return f"cloud_unreachable_{entry_id}"


def device_issue_id(dsn: str) -> str:
    return f"device_offline_{dsn}"


class FglAirCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll all registered devices and cache their property dicts."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: FglAirApi,
        devices: list[dict],
        entry_id: str = "",
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.hass = hass
        self.api = api
        self.entry_id = entry_id
        # Keyed by DSN for fast lookup; refreshed on every poll
        self.devices: dict[str, dict] = {
            d["device"]["dsn"]: d["device"] for d in devices
        }
        self._cloud_failures = 0
        self._offline_issues: set[str] = set()

    # ------------------------------------------------------------------
    # Repairs (Settings → System → Repairs)
    # ------------------------------------------------------------------

    def _device_name(self, dsn: str) -> str:
        dev = self.devices.get(dsn, {})
        return dev.get("friendly_name") or dev.get("product_name") or dsn

    def _set_device_offline_issue(self, dsn: str, offline: bool) -> None:
        issue_id = device_issue_id(dsn)
        if offline and dsn not in self._offline_issues:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="device_offline",
                translation_placeholders={"name": self._device_name(dsn), "dsn": dsn},
            )
            self._offline_issues.add(dsn)
        elif not offline and dsn in self._offline_issues:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            self._offline_issues.discard(dsn)

    def _cloud_failed(self, exc: BaseException) -> None:
        self._cloud_failures += 1
        if self._cloud_failures == CLOUD_FAILURE_THRESHOLD:
            _LOGGER.warning("FGLair cloud unreachable: %s", exc)
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                cloud_issue_id(self.entry_id),
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="cloud_unreachable",
                translation_placeholders={"error": str(exc) or type(exc).__name__},
            )

    def _cloud_ok(self) -> None:
        if self._cloud_failures >= CLOUD_FAILURE_THRESHOLD:
            _LOGGER.info("FGLair cloud connection restored")
            ir.async_delete_issue(self.hass, DOMAIN, cloud_issue_id(self.entry_id))
        self._cloud_failures = 0

    def clear_issues(self) -> None:
        """Remove every Repairs issue this coordinator raised (on unload)."""
        ir.async_delete_issue(self.hass, DOMAIN, cloud_issue_id(self.entry_id))
        for dsn in list(self._offline_issues):
            ir.async_delete_issue(self.hass, DOMAIN, device_issue_id(dsn))
        self._offline_issues.clear()

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        last_exc: BaseException | None = None
        cloud_reached = False

        # Refresh connection_status for all devices
        try:
            fresh = await self.api.get_devices_with_retry()
            cloud_reached = True
            for d in fresh:
                dev = d["device"]
                dsn = dev["dsn"]
                if dsn in self.devices:
                    self.devices[dsn] = dev
        except Exception as exc:  # noqa: BLE001
            if is_auth_error(exc):
                raise ConfigEntryAuthFailed(f"FGLair rejected the credentials: {exc}") from exc
            _LOGGER.debug("Could not refresh device list: %s", exc)
            last_exc = exc

        for dsn in self.devices:
            # Without a fresh device list the cached status may be stale, so
            # only trust it (and touch Repairs) when the cloud answered.
            connection_status = self.devices[dsn].get("connection_status", "Online")
            if cloud_reached:
                self._set_device_offline_issue(dsn, connection_status != "Online")
            if connection_status != "Online":
                _LOGGER.debug("Device %s is offline (status: %s)", dsn, connection_status)
                result[dsn] = {"__online": False}
                continue

            try:
                props = await self.api.get_properties_with_retry(dsn)
                cloud_reached = True
                props["__online"] = True
                result[dsn] = props

                # FGL devices: trigger a fresh sensor read from the AC unit by
                # writing get_prop=1. The AC responds by pushing a new
                # display_temperature to the cloud; the next poll picks it up.
                # Template B units have no room temperature in the app, so skip them.
                model = self.devices[dsn].get("oem_model")
                if "get_prop" in props and device_type(model) == "fgl":
                    try:
                        await self.api.set_device_property(dsn, "get_prop", 1)
                    except Exception:  # noqa: BLE001
                        pass  # Non-critical; next poll reads whatever the cloud has

            except Exception as exc:  # noqa: BLE001
                if is_auth_error(exc):
                    raise ConfigEntryAuthFailed(
                        f"FGLair rejected the credentials: {exc}"
                    ) from exc
                _LOGGER.warning("Failed to update %s: %s", dsn, exc)
                last_exc = exc
                # Keep the last known state if we have one
                if self.data and dsn in self.data:
                    result[dsn] = self.data[dsn]

        if cloud_reached:
            self._cloud_ok()
            return result

        # Nothing answered: the cloud (or our internet connection) is down.
        assert last_exc is not None
        self._cloud_failed(last_exc)
        if not self.data or self._cloud_failures >= CLOUD_FAILURE_THRESHOLD:
            # Entities become unavailable instead of showing stale state
            raise UpdateFailed(f"FGLair cloud unreachable: {last_exc}") from last_exc
        # Short blip: keep the last known state for a couple of polls
        return result
