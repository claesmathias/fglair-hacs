"""FGLair / Hisense AC integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import aiohttp

from .api import FglAirApi, is_auth_error
from .const import DOMAIN, CONF_APP, CONF_USERNAME, CONF_PASSWORD
from .coordinator import FglAirCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = FglAirApi(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_APP],
        session,
    )

    try:
        await api.authenticate()
        devices = await api.get_devices()
    except aiohttp.ClientError as exc:
        if is_auth_error(exc):
            # Starts the re-authentication flow (shown under Settings)
            raise ConfigEntryAuthFailed(f"FGLair rejected the credentials: {exc}") from exc
        raise ConfigEntryNotReady(f"Cannot connect to FGLair API: {exc}") from exc
    except TimeoutError as exc:
        raise ConfigEntryNotReady(f"Timed out connecting to FGLair API: {exc}") from exc

    coordinator = FglAirCoordinator(hass, api, devices, entry.entry_id)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        data["coordinator"].clear_issues()
    return unload_ok
