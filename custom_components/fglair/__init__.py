"""FGLair / Hisense AC integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import aiohttp

from .api import FglAirApi
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
    except aiohttp.ClientResponseError as exc:
        raise ConfigEntryNotReady(f"Authentication failed: {exc}") from exc
    except aiohttp.ClientError as exc:
        raise ConfigEntryNotReady(f"Cannot connect to FGLair API: {exc}") from exc

    coordinator = FglAirCoordinator(hass, api, devices)
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
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
