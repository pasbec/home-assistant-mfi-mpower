"""Config flow for Ubiquiti mFi mPower integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from . import api
from .const import DEFAULT_TIMEOUT, DEFAULTS, DOMAIN

_LOGGER = logging.getLogger(__name__)


def create_schema(data=None, conf: tuple | list | None = None):
    """Construct schema from config data."""
    if data is None:
        data = DEFAULTS

    schema = {
        vol.Required(
            CONF_HOST, default=data.get(CONF_HOST, DEFAULTS[CONF_HOST])
        ): cv.string,
        vol.Required(
            CONF_USERNAME, default=data.get(CONF_USERNAME, DEFAULTS[CONF_USERNAME])
        ): cv.string,
        vol.Required(
            CONF_PASSWORD, default=data.get(CONF_PASSWORD, DEFAULTS[CONF_PASSWORD])
        ): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=data.get(CONF_SCAN_INTERVAL, DEFAULTS[CONF_SCAN_INTERVAL]),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=DEFAULT_TIMEOUT,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="seconds",
            ),
        ),
    }

    if conf is not None:
        for key in list(schema.keys()):
            if key.schema not in conf:
                schema.pop(key)

    return vol.Schema(schema)


async def validate_data(hass: HomeAssistant, data: dict[str, Any]) -> str | None:
    """Validate the config data allows us to connect."""

    try:
        api_device = await api.create_device(hass, data)
    except Exception as exc:  # pylint: disable=broad-except
        _LOGGER.debug("Device creation failed: %s", exc)
        return "input_error"

    try:
        await api_device.login()
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


class MPowerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flows for Ubiquiti mFi mPower."""

    VERSION = 1

    _reauth_entry: config_entries.ConfigEntry

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        data = {}
        error = None

        if user_input:
            data.update(user_input)
            error = await validate_data(self.hass, data=data)

            # NOTE: If data is validated, a new entry is created
            if not error:
                return self.async_create_entry(title=user_input[CONF_HOST], data=data)

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
