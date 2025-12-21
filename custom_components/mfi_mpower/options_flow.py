"""Options flow for Ubiquiti mFi mPower integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import OptionsFlow
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers import config_validation as cv

from .const import DEFAULTS, DEFAULT_TIMEOUT


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


class MPowerOptionsFlowHandler(OptionsFlow):
    """Handle options flows for Ubiquiti mFi mPower."""

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        data = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=create_schema(data),
        )
