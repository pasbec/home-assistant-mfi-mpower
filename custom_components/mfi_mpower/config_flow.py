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
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from . import api, CONFIG_VERSION
from .const import DOMAIN
from .schema import create_schema

_LOGGER = logging.getLogger(__name__)


# TODO: Use OptionsFlowWithReload with homeassistant>=2025.8.0
#       and remove async_update_listener in __init__.py afterwards
class MPowerOptionsFlow(OptionsFlow):
    """Handle options flows for Ubiquiti mFi mPower."""

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        config_entry = self.config_entry
        data = {**config_entry.data, **config_entry.options}

        # User input is available
        if user_input is not None:
            # Update the config entry and finish the flow
            return self.async_create_entry(data=user_input)

        # Show the form to the user
        return self.async_show_form(
            step_id="init",
            data_schema=create_schema(data, conf=(CONF_SCAN_INTERVAL,)),
        )


class MPowerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flows for Ubiquiti mFi mPower."""

    VERSION, MINOR_VERSION = CONFIG_VERSION.major, CONFIG_VERSION.minor

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> MPowerOptionsFlow:
        """Create the options flow."""
        return MPowerOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the (initial) setup flow."""
        data = {}
        error = None

        # User input is available
        if user_input:
            # Update data with user input
            data.update(user_input)

            # Validate data by creating device instance
            (api_device, error) = await api.create_device_for_flow(self.hass, data=data)

            # Proceed only if API device is available and no error occurred
            if not error and api_device and api_device.has_data:
                # List current and other config entries
                _LOGGER.debug(
                    "Setting up config entry for device: %s (%s)",
                    api_device.host,
                    api_device.mac,
                )
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    _LOGGER.debug(
                        "Existing config entry for device: %s (%s)",
                        entry.data.get(CONF_HOST),
                        entry.unique_id,
                    )

                # Set unique ID for the config flow
                await self.async_set_unique_id(api_device.mac)

                # Abort the flow if a flow with the same unique ID exists
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: api_device.host}
                )

                # Create the config entry and finish the flow
                return self.async_create_entry(
                    title=api.create_title(user_input[CONF_HOST]),
                    data=data,
                )
            elif not error:
                error = "unknown"

        # Show the form to the user
        return self.async_show_form(
            step_id="user",
            data_schema=create_schema(data),
            errors=None if error is None else {"base": error},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the reconfiguration flow."""
        config_entry = self._get_reconfigure_entry()
        data = config_entry.data.copy()
        error = None

        # User input is available
        if user_input:
            # Update data with user input
            data.update(user_input)

            # Validate data by creating device instance
            (api_device, error) = await api.create_device_for_flow(self.hass, data=data)

            # Proceed only if API device is available and no error occurred
            if not error and api_device and api_device.has_data:
                # List current and other config entries
                _LOGGER.debug(
                    "Reconfiguring config entry for device: %s (%s)",
                    api_device.host,
                    api_device.mac,
                )
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    _LOGGER.debug(
                        "Existing config entry for device: %s (%s)",
                        entry.data.get(CONF_HOST),
                        entry.unique_id,
                    )

                # Set unique ID for the config flow
                await self.async_set_unique_id(api_device.mac)

                # Abort the flow if an entry with the unique ID was found
                self._abort_if_unique_id_mismatch()

                # Reconfigure the config entry and finish the flow
                return self.async_update_reload_and_abort(
                    config_entry,
                    data_updates=data,
                )
            elif not error:
                error = "unknown"

        # Show the form to the user
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=create_schema(data),
            errors=None if error is None else {"base": error},
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle the reauthentication flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the reauthentication confirmation dialog."""
        config_entry = self._get_reauth_entry()
        data = config_entry.data.copy()
        error = None

        # Use input is available
        if user_input:
            # Update data with user input
            data.update(user_input)

            # Validate data by creating device instance
            (_, error) = await api.create_device_for_flow(self.hass, data=data)

            # Proceed only if no error occurred
            if not error:
                # Update the config entry with new data
                self.hass.config_entries.async_update_entry(config_entry, data=data)

                # Reload the config entry
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(config_entry.entry_id)
                )

                # Abort the flow indicating success
                return self.async_abort(reason="reauth_successful")

        # Show the form to the user
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=create_schema(data, conf=(CONF_USERNAME, CONF_PASSWORD)),
            errors=None if error is None else {"base": error},
        )
