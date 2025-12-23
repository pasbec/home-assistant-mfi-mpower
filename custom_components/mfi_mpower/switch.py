"""Support for Ubiquiti mFi mPower switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components import switch
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import EntityCategory
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
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubiquiti mFi mPower switches based on config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
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
        *[MPowerLockSwitchEntity(coordinator, e) for e in api_entities],
        *[MPowerOutletSwitchEntity(coordinator, e) for e in api_entities],
    ]

    await coordinator.async_migrate_old_entity_unique_ids(entities)

    return entities


class MPowerSwitchEntity(MPowerCoordinatorEntity, SwitchEntity):
    """Coordinated outlet switch entity for Ubiquiti mFi mPower."""

    _domain: str = switch.DOMAIN


class MPowerLockSwitchEntity(MPowerSwitchEntity):
    """Coordinated lock switch entity for Ubiquiti mFi mPower."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_translation_key = "lock"

    def _handle_attr_update(self) -> None:
        """Handle attribute updates from API data."""
        self._attr_is_on = self.api_entity.locked

    @property
    def icon(self) -> str | None:
        """Return the icon of the lock switch."""
        if self.api_entity.locked:
            return "mdi:lock"
        return "mdi:lock-open"

    @property
    def is_on(self) -> bool | None:
        """Return True if the port is locked."""
        return self.api_entity.locked

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Lock the lock switch."""
        await self.api_entity.lock(refresh=False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlock the lock switch."""
        await self.api_entity.unlock(refresh=False)
        await self.coordinator.async_request_refresh()


class MPowerOutletSwitchEntity(MPowerSwitchEntity):
    """Coordinated outlet switch entity for Ubiquiti mFi mPower."""

    _attr_device_class = SwitchDeviceClass.OUTLET
    _attr_translation_key = None
    _attr_name = None

    @property
    def _old_unique_ids(self) -> list[str]:
        """Return additional old unique IDs of the outlet switch."""
        return [f"{self._old_unique_id}-{k}" for k in ("switch", "outlet")]

    def _handle_attr_update(self) -> None:
        """Handle attribute updates from API data."""
        self._attr_available = not self.api_entity.locked
        self._attr_is_on = self.api_entity.output

    @property
    def available(self) -> bool:
        """Return the availability of the outlet switch."""
        if self.api_entity.locked:
            return False
        return super().available

    @property
    def icon(self) -> str | None:
        """Return the icon of the outlet switch."""
        if self.api_device.is_eu_model:
            return "mdi:power-socket-de"
        return "mdi:power-socket-us"

    @property
    def is_on(self) -> bool | None:
        """Return True if the outlet is on."""
        return self.api_entity.output

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the outlet switch on."""
        await self.api_entity.turn_on(refresh=False)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the outlet switch off."""
        await self.api_entity.turn_off(refresh=False)
        await self.coordinator.async_request_refresh()
