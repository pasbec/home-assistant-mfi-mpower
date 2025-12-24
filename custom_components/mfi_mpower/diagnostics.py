"""Constants for the Ubiquiti mFi mPower integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

TO_REDACT = {CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    return {
        "version": f"{entry.version}.{entry.minor_version}",
        "unique_id": entry.unique_id,
        "title": entry.title,
        "data": async_redact_data(entry.data, TO_REDACT),
        "options": async_redact_data(entry.options, TO_REDACT),
    }


# async def async_get_device_diagnostics(
#     hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
# ) -> dict[str, Any]:
#     return {}
#     """Return diagnostics for a device."""
#     appliance = _get_appliance_by_device_id(hass, device.id)
#     return {
#         "details": async_redact_data(appliance.raw_data, TO_REDACT),
#         "data": appliance.data,
#     }
