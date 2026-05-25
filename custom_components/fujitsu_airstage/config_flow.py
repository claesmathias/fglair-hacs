"""Config flow for the FGLair integration."""
from __future__ import annotations

import logging
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


class FglAirConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup UI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = FglAirApi(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_APP],
                session,
            )
            try:
                await api.authenticate()
                devices = await api.get_devices()
                if not devices:
                    errors["base"] = "no_devices"
            except aiohttp.ClientResponseError as exc:
                _LOGGER.debug("Auth error: %s", exc)
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError as exc:
                _LOGGER.debug("Connection error: %s", exc)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during authentication")
                errors["base"] = "unknown"

            if not errors:
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
