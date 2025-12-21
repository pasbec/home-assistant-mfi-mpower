"""Support for Ubiquiti mFi mPower selects."""

from __future__ import annotations

import logging

from homeassistant.components import select
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import api
from .config_flow import create_schema
from .const import DOMAIN
from .update_coordinator import MPowerCoordinatorEntity, MPowerDataUpdateCoordinator

PLATFORM_SCHEMA = select.PLATFORM_SCHEMA.extend(create_schema().schema)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Ubiquiti mFi mPower selects based on config."""
    coordinator = await api.create_coordinator(hass, config[DOMAIN])
    entities = await async_create_entities(coordinator)
    async_add_entities(entities, False)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubiquiti mFi mPower selects based on config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = await async_create_entities(coordinator)
    async_add_entities(entities, False)


async def async_create_entities(
    coordinator: MPowerDataUpdateCoordinator,
) -> list[MPowerSelectEntity]:
    """Create switch entities from Ubiquiti mFi mPower switches."""

    entities = [MPowerLEDSelectEntity(coordinator)]

    await coordinator.async_migrate_old_entity_unique_ids(entities)

    return entities


class MPowerSelectEntity(MPowerCoordinatorEntity, SelectEntity):
    """Coordinated select entity for Ubiquiti mFi mPower."""

    domain: str = select.DOMAIN


class MPowerLEDSelectEntity(MPowerSelectEntity):
    """Coordinated select entity for Ubiquiti mFi mPower LED status."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = [e.name for e in api.MPowerLED]
    _attr_translation_key = "led"

    def _handle_attr_update(self) -> None:
        """Handle attribute updates from API data."""
        self._attr_current_option = self.api_device.led.name

    @property
    def unique_id(self) -> str:
        """Return the unique id of the select ."""
        return f"{self.api_device.unique_id}-led"

    async def async_select_option(self, option: str) -> None:
        """Change the select option."""
        await self.api_device.set_led(api.MPowerLED[option], refresh=False)
        await self.coordinator.async_request_refresh()
