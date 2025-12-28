"""Support for Ubiquiti mFi mPower buttons."""

from __future__ import annotations

import logging

from homeassistant.components import button
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import api
from .config_flow import create_schema
from .const import DOMAIN
from .update_coordinator import MPowerCoordinatorEntity, MPowerDataUpdateCoordinator

PLATFORM_SCHEMA = button.PLATFORM_SCHEMA.extend(create_schema().schema)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Ubiquiti mFi mPower buttons based on config."""
    coordinator = await api.create_coordinator(hass, config[DOMAIN])
    entities = await async_create_entities(coordinator)
    async_add_entities(entities, False)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubiquiti mFi mPower buttons based on config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = await async_create_entities(coordinator)
    async_add_entities(entities, False)


async def async_create_entities(
    coordinator: MPowerDataUpdateCoordinator,
) -> list[MPowerButtonEntity]:
    """Create Ubiquiti mFi mPower button entities."""

    entities = [MPowerRestartButtonEntity(coordinator)]

    await coordinator.async_migrate_old_entity_unique_ids(entities)

    return entities


class MPowerButtonEntity(MPowerCoordinatorEntity, ButtonEntity):
    """Coordinated button entity for Ubiquiti mFi mPower."""

    _domain: str = button.DOMAIN


class MPowerRestartButtonEntity(MPowerButtonEntity):
    """Coordinated button entity for Ubiquiti mFi mPower restarts."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:restart"
    _attr_translation_key = "restart"

    async def async_press(self) -> None:
        """Press the button."""
        await self.api_device.reboot()
