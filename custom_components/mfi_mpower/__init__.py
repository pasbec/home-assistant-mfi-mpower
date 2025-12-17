"""The Ubiquiti mFi mPower integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry

from . import api
from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = await api.create_coordinator(hass, dict(entry.data))
    api_device = coordinator.api_device

    hass.data[DOMAIN][entry.entry_id] = coordinator

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        configuration_url=str(api_device.url),
        connections={(dr.CONNECTION_NETWORK_MAC, api_device.hwaddr)},
        identifiers={(DOMAIN, api_device.unique_id)},
        manufacturer=api_device.manufacturer,
        name=api_device.name,
        model=api_device.model,
        sw_version=api_device.fwversion,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    device_id = device_entry.id

    entity_registry = er.async_get(hass)
    entity_device_ids = {entry.device_id for entry in entity_registry.entities.values()}

    # Allow only removal of orphaned port devices
    if device_id not in entity_device_ids:
        return True

    # Allow removal of port devices
    if device_entry.via_device_id is not None:
        return True

    return False
