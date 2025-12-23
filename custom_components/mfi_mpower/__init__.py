"""The Ubiquiti mFi mPower integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry

from . import api
from .const import CONF_HOST, DOMAIN

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    title = api.create_title(config_entry.data[CONF_HOST])
    if config_entry.title != title:
        hass.config_entries.async_update_entry(config_entry, title=title)
    hass.data.setdefault(DOMAIN, {})

    # Get data merged with options
    data = {**config_entry.data, **config_entry.options}

    coordinator = await api.create_coordinator(
        hass=hass, data=data, config_entry=config_entry
    )
    api_device = coordinator.api_device

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    # Add update listener to reload integration after options changes
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_reload))

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        configuration_url=f"http://{api_device.host}",
        connections={
            (dr.CONNECTION_NETWORK_MAC, hwaddr)
            for hwaddr in api_device.hwaddrs.values()
        },
        hw_version=api_device.hw_version,
        identifiers={(DOMAIN, api_device.unique_id)},
        manufacturer=api_device.manufacturer,
        name=api_device.name,
        model=api_device.model,
        model_id=api_device.model_id,
        sw_version=api_device.sw_version,
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_update_reload(hass: HomeAssistant, config_entry: ConfigEntry):
    """Listener to trigger a reload of the config entry."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(config_entry.entry_id)

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
