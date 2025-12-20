"""Support for Ubiquiti mFi mPower switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components import switch
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import api
from .config_flow import create_schema
from .const import DOMAIN
from .update_coordinator import MPowerCoordinatorEntity, MPowerDataUpdateCoordinator

PLATFORM_SCHEMA = switch.PLATFORM_SCHEMA.extend(create_schema().schema)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Ubiquiti mFi mPower switches based on config."""
    coordinator = await api.create_coordinator(hass, config[DOMAIN])
    entities = await async_create_entities(coordinator)
    async_add_entities(entities, False)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubiquiti mFi mPower switches based on config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = await async_create_entities(coordinator)
    async_add_entities(entities, False)


async def async_create_entities(
    coordinator: MPowerDataUpdateCoordinator,
) -> list[MPowerSwitchEntity]:
    """Create switch entities from Ubiquiti mFi mPower switches."""
    api_device = coordinator.api_device

    try:
        api_entities: list[api.MPowerSwitch] = await api_device.create_switches()
    except Exception as exc:
        raise PlatformNotReady from exc

    entities: list[MPowerSwitchEntity] = [
        MPowerSwitchEntity(e, coordinator) for e in api_entities
    ]

    return entities


class MPowerSwitchEntity(MPowerCoordinatorEntity, SwitchEntity):
    """Coordinated switch entity for Ubiquiti mFi mPower switches."""

    api_entity: api.MPowerSwitch

    domain: str = switch.DOMAIN

    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_name = None

    @property
    def available(self) -> bool:
        """Return the availability of the switch."""
        if self.api_entity.locked:
            return False
        return super().available

    @property
    def unique_id(self) -> str:
        """Return the unique id of the switch."""
        return f"{self.api_entity.unique_id}-switch"

    @property
    def icon(self) -> str | None:
        """Return the icon of the switch."""
        if self.api_device.eu_model:
            return "mdi:power-socket-de"
        return "mdi:power-socket-us"

    @property
    def is_on(self) -> bool | None:
        """Return True if the switch is on."""
        return self.api_entity.output

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.api_entity.turn_on(refresh=False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.api_entity.turn_off(refresh=False)
        await self.coordinator.async_request_refresh()
