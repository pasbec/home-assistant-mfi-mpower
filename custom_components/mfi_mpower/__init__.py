"""The Ubiquiti mFi mPower integration."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_HOST, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry

from . import api
from .const import DOMAIN
from .version import Version

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.SELECT,
]

CONFIG_VERSION = Version(1, 2)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    data = {**config_entry.data, **config_entry.options}

    # Create domain data dict if it does not exist
    hass.data.setdefault(DOMAIN, {})

    # Update config entry title
    hass.config_entries.async_update_entry(
        config_entry, title=api.create_title(config_entry.data[CONF_HOST])
    )

    # Create data update coordinator
    coordinator = await api.create_coordinator(
        hass=hass, data=data, config_entry=config_entry
    )

    # Register coordinator with entry ID in hass data
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    # Add update listener to reload integration after options changes
    config_entry.async_on_unload(
        config_entry.add_update_listener(async_config_entry_update_listener)
    )

    # Get API device from coordinator
    api_device = coordinator.api_device

    # Register device in device registry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        configuration_url=f"http://{api_device.hostname}",
        connections={
            (dr.CONNECTION_NETWORK_MAC, hwaddr) for hwaddr in api_device.macs.values()
        },
        hw_version=api_device.revision,
        identifiers={(DOMAIN, api_device.mac)},
        manufacturer=api_device.manufacturer,
        name=api_device.name,
        model=api_device.model,
        model_id=api_device.model_id,
        sw_version=api_device.firmware,
    )

    # Add listeners ...
    if not hass.data[DOMAIN].get("listeners_registered"):
        # ... for device registry updates
        hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
            create_device_registry_update_listener(hass),
        )

        # ... for entity registry updates
        hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            create_entity_registry_update_listener(hass),
        )

        hass.data[DOMAIN]["listeners_registered"] = True

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_config_entry_update_listener(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Listener to trigger a reload of the config entry."""
    await hass.config_entries.async_reload(config_entry.entry_id)


def create_device_registry_update_listener(
    hass: HomeAssistant,
) -> Callable[[Event], Awaitable[None]]:
    async def listener(event: Event) -> None:
        _LOGGER.debug("Device registry updated: %s", event.data)
        if device_id := event.data.get("device_id"):
            device_registry = dr.async_get(hass)
            if device := device_registry.async_get(device_id):
                changes = event.data.get("changes", {}).copy()
                for key in changes:
                    changes[key] = getattr(device, key, None)
                _LOGGER.debug("Device registry changes: %s", changes)

    return listener


def create_entity_registry_update_listener(
    hass: HomeAssistant,
) -> Callable[[Event], Awaitable[None]]:
    async def listener(event: Event) -> None:
        _LOGGER.debug("Entity registry updated: %s", event.data)
        if entity_id := event.data.get("entity_id"):
            entity_registry = er.async_get(hass)
            if entry := entity_registry.async_get(entity_id):
                changes = event.data.get("changes", {}).copy()
                for key in changes:
                    changes[key] = getattr(entry, key, None)
                _LOGGER.debug("Entity registry changes: %s", changes)

    return listener


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

    # Allow only removal of orphaned devices
    if device_id not in entity_device_ids:
        return True

    return False


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate config entry in case of version changes."""
    version = Version(config_entry.version, config_entry.minor_version)
    unique_id = config_entry.unique_id
    title = config_entry.title
    data = dict(config_entry.data)
    options = dict(config_entry.options)

    # Log migration info
    _LOGGER.debug(
        "Migrating config for %s from version %s to %s", title, version, CONFIG_VERSION
    )

    if version > CONFIG_VERSION:
        # Downgrades from a future version are not supported
        _LOGGER.error("Config version downgrades are not supported")
        return False

    if version < Version(1, 2):
        # Add missing unique ID to config entry
        try:
            api_device: api.MPowerDevice = api.create_device(hass, data)
            await api_device.refresh()
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Device creation failed during migration: %s", exc)
            return False
        unique_id = api_device.mac

        # Remove deprecated SSL options
        for key in (CONF_SSL, CONF_VERIFY_SSL):
            data.pop(key, None)
            options.pop(key, None)

    # Update config entry to new version
    hass.config_entries.async_update_entry(
        config_entry,
        version=CONFIG_VERSION.major,
        minor_version=CONFIG_VERSION.minor,
        unique_id=unique_id,
        title=title,
        data=data,
        options=options,
    )

    return True
