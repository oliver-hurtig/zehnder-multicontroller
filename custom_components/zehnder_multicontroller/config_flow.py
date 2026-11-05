"""Adds config flow for Zehnder Multicontroller."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigFlow
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.config_entries import OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PASSWORD
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.core import callback

from .const import CONF_USE_CLIMATE
from .const import DEFAULT_USE_CLIMATE
from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)

DEFAULT_HOST = "https://api.rainmaker.espressif.com/v1/"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    from .api import RainmakerAPI

    api = RainmakerAPI(hass, data[CONF_HOST], data[CONF_USERNAME], data[CONF_PASSWORD])
    await api.async_connect()

    return {"title": "Zehnder Multicontroller"}


class ZehnderMulticontrollerFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zehnder Multicontroller."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return ZehnderMulticontrollerOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step.

        Validate credentials using `validate_input`. Provide specific user-facing
        errors for authentication or connectivity failures and fall back to a
        generic unknown error for anything else.
        """
        from .api import RainmakerAuthError
        from .api import RainmakerConnectionError

        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        try:
            info = await validate_input(self.hass, user_input)
        except RainmakerAuthError:
            errors["base"] = "auth"
        except RainmakerConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:  # pragma: no cover - unexpected
            _LOGGER.exception("Unexpected exception during config flow validation")
            errors["base"] = "unknown"
        else:
            # Use a stable, specific unique id (host + username) so multiple
            # accounts pointing to the same host can be distinguished.
            host = (user_input.get(CONF_HOST) or "").rstrip("/")
            username = user_input.get(CONF_USERNAME) or ""
            unique_id = f"{host}|{username}" if username else host
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=info["title"], data=user_input)

        # If we reach here, validation failed — redisplay form with errors
        return self.async_show_form(data_schema=STEP_USER_DATA_SCHEMA, errors=errors)


class ZehnderMulticontrollerOptionsFlow(OptionsFlow):
    """Options: choose between the climate entity and individual entities."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_USE_CLIMATE, DEFAULT_USE_CLIMATE)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_USE_CLIMATE, default=current): bool}
            ),
        )
