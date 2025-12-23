"""Config flow for Ubiquiti mFi mPower integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from . import api
from .const import CONF_SCAN_INTERVAL, DOMAIN
from .schema import create_schema


# TODO: Use OptionsFlowWithReload with homeassistant>=2025.8.0
#       and remove async_update_listener in __init__.py afterwards
class MPowerOptionsFlow(OptionsFlow):
    """Handle options flows for Ubiquiti mFi mPower."""

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        # User input is available
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        # Get data merged with options
        data = {**self.config_entry.data, **self.config_entry.options}

        # Show the form to the user
        return self.async_show_form(
            step_id="init",
            data_schema=create_schema(data, conf=(CONF_SCAN_INTERVAL,)),
        )


class MPowerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flows for Ubiquiti mFi mPower."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> MPowerOptionsFlow:
        """Create the options flow."""
        return MPowerOptionsFlow()

    @property
    def config_entry(self) -> ConfigEntry | None:
        """Return the config entry being configured."""
        return self.hass.config_entries.async_get_entry(self.context["entry_id"])

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
            if api_device is not None and not error:
                # Set unique ID for the config flow
                # TODO: Change unique ID of the API to use only hwaddr
                # await self.async_set_unique_id(api_device.unique_id)
                await self.async_set_unique_id(api_device.hwaddr)

                # Abort the flow if a config entry with the same unique ID exists
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: api_device.host}
                )

                # Create the config entry
                return self.async_create_entry(
                    title=api.create_title(user_input[CONF_HOST]),
                    data=data,
                )

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
        config_entry = self.config_entry
        data = config_entry.data.copy()
        error = None

        # User input is available
        if user_input:
            # Update data with user input
            data.update(user_input)

            # Validate data by creating device instance
            (api_device, error) = await api.create_device_for_flow(self.hass, data=data)

            # Proceed only if API device is available and no error occurred
            if api_device is not None and not error:
                # Get the unique ID of the flow
                unique_id = self.unique_id

                # Set unique ID for the config flow
                # TODO: Change unique ID of the API to use only hwaddr
                # await self.async_set_unique_id(api_device.unique_id)
                await self.async_set_unique_id(api_device.hwaddr)

                # Abort the flow if the unique ID was set during initial setup and does not match
                if unique_id is not None:
                    self._abort_if_unique_id_mismatch()

                # Reconfigure the config entry
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates=data,
                )

        # Show the form to the user
        return self.async_show_form(
            step_id="reconfigure", data_schema=create_schema(data)
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle the reauthentication flow."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the reauthentication confirmation dialog."""
        config_entry = self.config_entry
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
