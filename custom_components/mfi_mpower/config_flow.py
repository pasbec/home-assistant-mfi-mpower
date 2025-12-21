"""Config flow for Ubiquiti mFi mPower integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from . import api
from .const import DOMAIN
from .options_flow import create_schema, MPowerOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)


async def validate_data(hass: HomeAssistant, data: dict[str, Any]) -> str | None:
    """Validate the config data ."""

    try:
        api_device = await api.create_device(hass, data)
    except Exception as exc:  # pylint: disable=broad-except
        _LOGGER.debug("Device creation failed: %s", exc)
        return "input_error"

    try:
        await api_device.session.connect()
    except api.MPowerConnectionError as exc:
        _LOGGER.debug("Connection failed: %s", exc)
        return "cannot_connect"
    except api.MPowerAuthenticationError as exc:
        _LOGGER.debug("Authentication failed: %s", exc)
        return "invalid_auth"
    except Exception as exc:  # pylint: disable=broad-except
        _LOGGER.exception("Unhandled exception occurred: %s", exc)
        return "unknown"

    return None


class MPowerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flows for Ubiquiti mFi mPower."""

    VERSION = 1

    _reauth_entry: ConfigEntry

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MPowerOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step."""
        data = {}
        error = None

        if user_input:
            data.update(user_input)
            error = await validate_data(self.hass, data=data)

            # NOTE: If data is validated, a new entry is created
            if not error:
                return self.async_create_entry(
                    title=api.create_title(user_input[CONF_HOST]),
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=create_schema(data),
            errors=None if error is None else {"base": error},
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle a reauthorization flow request."""
        reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if reauth_entry is not None:
            self._reauth_entry = reauth_entry
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the reauth confirmation step."""
        data = dict(self._reauth_entry.data)
        error = None

        if user_input:
            data.update(user_input)
            error = await validate_data(self.hass, data=data)

            # NOTE: If data is validated, the entry is updated and reloaded
            if not error:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry, data=data
                )
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=create_schema(data, conf=(CONF_USERNAME, CONF_PASSWORD)),
            errors=None if error is None else {"base": error},
        )
