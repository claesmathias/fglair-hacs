"""Config flow for the FGLair integration."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FglAirApi
from .const import DOMAIN, CONF_APP, CONF_USERNAME, CONF_PASSWORD, APP_LABELS

_LOGGER = logging.getLogger(__name__)

_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_APP, default="fglair-eu"): vol.In(APP_LABELS),
    }
)


async def _validate(hass, username: str, password: str, app: str) -> str | None:
    """Try to sign in and list devices; return an error key or None."""
    api = FglAirApi(username, password, app, async_get_clientsession(hass))
    try:
        await api.authenticate()
        devices = await api.get_devices()
    except aiohttp.ClientResponseError as exc:
        _LOGGER.debug("Auth error: %s", exc)
        return "invalid_auth"
    except (aiohttp.ClientError, TimeoutError) as exc:
        _LOGGER.debug("Connection error: %s", exc)
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error during authentication")
        return "unknown"
    if not devices:
        return "no_devices"
    return None


class FglAirConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup UI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            if error := await _validate(
                self.hass,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_APP],
            ):
                errors["base"] = error
            else:
                unique_id = f"{user_input[CONF_APP]}_{user_input[CONF_USERNAME]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"FGLair ({user_input[CONF_USERNAME]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Started by HA when the cloud rejects the stored credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            if error := await _validate(
                self.hass, data[CONF_USERNAME], data[CONF_PASSWORD], data[CONF_APP]
            ):
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"username": entry.data[CONF_USERNAME]},
        )
