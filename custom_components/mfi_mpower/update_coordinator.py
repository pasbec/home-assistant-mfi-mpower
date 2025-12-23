"""Update coordinator helpers for the Ubiquiti mFi mPower integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from datetime import timedelta
import logging

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import SLOW_SETUP_MAX_WAIT
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import slugify

from . import api
from .const import DEFAULT_TIMEOUT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MPowerDataUpdateCoordinator(DataUpdateCoordinator):
    """Ubiquiti mFi mPower data update coordinator."""

    _api_device: api.MPowerDevice

    def __init__(
        self,
        hass: HomeAssistant,
        api_device: api.MPowerDevice,
        scan_interval: float,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        # Set the API device
        self._api_device = api_device

        # Initialize the generic coordinator
        super().__init__(
            hass,
            logger=_LOGGER,
            name=api.create_title(api_device.hostname),
            update_interval=timedelta(seconds=scan_interval),
            config_entry=config_entry,
        )

    @property
    def api_device(self) -> api.MPowerDevice:
        """Return the mFi mPower device from the coordinator."""
        return self._api_device

    async def _async_update_data(self) -> list[dict]:
        """Fetch data from the device."""
        try:
            has_data = self.api_device.has_data
            timeout = DEFAULT_TIMEOUT if has_data else SLOW_SETUP_MAX_WAIT
            async with async_timeout.timeout(timeout):
                await api.update_device(self.api_device)
        except asyncio.TimeoutError as exc:
            raise asyncio.TimeoutError(exc) from exc
        except api.MPowerAuthenticationError as exc:
            raise ConfigEntryAuthFailed(exc) from exc
        except Exception as exc:
            raise UpdateFailed(exc) from exc

        return self.api_device.data

    async def async_migrate_old_entity_unique_ids(
        self,
        entities: list[MPowerCoordinatorEntity],
    ) -> None:
        """Migrate old unique IDs for Ubiquiti mFi mPower entities."""
        # GEt registries
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        # Check all entities
        for entity in entities:
            # Get unique ID and entity ID
            unique_id = entity.unique_id
            entity_id = entity_registry.async_get_entity_id(
                entity.domain, DOMAIN, unique_id
            )

            # Check all old unique entity IDs
            for old_unique_id in entity.old_unique_ids:
                # Search for entity with old unique ID
                old_entity_id = entity_registry.async_get_entity_id(
                    entity.domain, DOMAIN, old_unique_id
                )
                if old_entity_id:
                    # Skip if new entity already exists
                    if entity_id:
                        _LOGGER.error(
                            "Duplicate entity found for unique ID %s with unique ID %s",
                            unique_id,
                            old_unique_id,
                        )
                    # Migrate old entity to new unique ID
                    else:
                        _LOGGER.info(
                            "Migrating entity for unique ID %s from unique ID %s",
                            unique_id,
                            old_unique_id,
                        )
                        entity_registry.async_update_entity(
                            old_entity_id,
                            new_unique_id=unique_id,
                        )

            # Check all old unique device IDs
            for old_device_id in entity.old_device_ids:
                old_device = device_registry.async_get_device(
                    identifiers={(DOMAIN, old_device_id)}
                )
                # Remove old devices from device registry
                if old_device:
                    device_registry.async_remove_device(old_device.id)


class MPowerCoordinatorEntity(CoordinatorEntity, ABC):
    """Coordinator entity baseclass for Ubiquiti mFi mPower entities."""

    _api_entity: api.MPowerEntity | None
    _api_unique_id: str | None
    _old_unique_id: str | None

    _attr_assumed_state = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MPowerDataUpdateCoordinator,
        api_entity: api.MPowerEntity | None = None,
    ) -> None:
        """Initialize the entity."""
        # Initialize the Coordinator entity
        super().__init__(coordinator)

        # Set the optional API entity
        self._api_entity = api_entity

        # Create the unique IDs (requires optional API entity)
        self._api_unique_id = self._create_unique_id()
        self._old_unique_id = self._create_unique_id(old=True)

        # Update attributes from initial data
        self._handle_attr_update()

    @property
    @abstractmethod
    def _domain(self) -> str:
        """The domain of the entity."""
        pass

    @property
    def domain(self) -> str:
        """Return the domain of the entity."""
        return self._domain

    def _create_unique_id(self, old=False) -> str:
        """Create the unique ID of the entity."""
        if old:
            macs = self.api_device.macs
            lan = api.MPowerNetwork.LAN.name.lower()
            wlan = api.MPowerNetwork.WLAN.name.lower()
            unique_id = f"{macs[lan]}-{macs[wlan]}"
        else:
            unique_id = self.api_device.mac
        if self.has_api_entity:
            unique_id = f"{unique_id}-{self.api_entity.port}"
        return unique_id

    @property
    def unique_id(self) -> list[str]:
        """Return the unique ID of the entity."""
        if self.translation_key:
            return f"{self._api_unique_id}-{self.translation_key}"
        return self._api_unique_id

    @property
    def old_unique_id(self) -> list[str]:
        """Return the old unique ID of the entity."""
        if self.translation_key:
            return f"{self._old_unique_id}-{self.translation_key}"
        return self._old_unique_id

    @property
    def _old_unique_ids(self) -> list[str]:
        """Return additional old unique IDs of the entity."""
        return []

    @property
    def old_unique_ids(self) -> list[str]:
        """Return all old unique IDs of the entity."""
        return [self.old_unique_id] + self._old_unique_ids

    @property
    def api_device(self) -> api.MPowerDevice:
        """Return the API device of the entity."""
        return self.coordinator.api_device

    @property
    def has_api_entity(self) -> bool:
        """Return the if the entity is connected to some API entity."""
        return self._api_entity is not None

    @property
    def api_entity(self) -> api.MPowerEntity | None:
        """Return the API entity of the entity."""
        if self.has_api_entity:
            # Ensure the API device matches the coordinator device
            assert self._api_entity.device == self.coordinator.api_device
            return self._api_entity
        return None

    @property
    def port_name(self) -> str | None:
        """Return the port name of the entity."""
        if self.has_api_entity:
            return f"Port {self.api_entity.port}"
        return None

    @property
    def old_device_ids(self) -> list[str]:
        """Return old device IDs of the entity."""
        return [self._old_unique_id]

    @property
    def device_id(self) -> str:
        """Return the device ID of the entity."""
        return self._api_unique_id

    @property
    def device_model(self) -> str:
        """Return the device model of the entity."""
        if self.has_api_entity:
            # return self.coordinator.name
            return f"{self.coordinator.name} {self.port_name}"
        return self.api_device.model

    @property
    def device_name(self) -> str:
        """Return the device name of the entity."""
        if self.has_api_entity:
            if self.api_entity.label:
                return self.api_entity.label
            else:
                return self.port_name
        return self.coordinator.name

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.device_name,
            manufacturer=self.api_device.manufacturer,
            model=self.device_model,
            via_device=(DOMAIN, self.api_device.mac),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Skip update without Home Assistant instance
        if self.hass is None:
            _LOGGER.error(
                "Home Assistant instance not set for entity %s, skipping update",
                self.unique_id,
            )
            return

        # Update coordinator name
        self.coordinator.name = api.create_title(self.api_device.hostname)

        # Get updated data from coordinator (return value from _async_update_data)
        data = self.coordinator.data

        # Skip update without data
        if data is None:
            _LOGGER.error(
                "Data for entity %s is invalid, skipping update", self.unique_id
            )
            return

        # Update data
        if self.has_api_entity:
            # Update API entity data
            try:
                self.api_entity.update(data)
            except api.MPowerDataError:
                _LOGGER.error(
                    "Port data for entity %s is invalid, skipping update",
                    self.unique_id,
                )
                return
        else:
            # Update APIdevice data
            self.api_device.update(data)

        # Get old device name
        old_device_name = self.device_info.get("name")
        new_device_name = self.device_name

        # Adjust device name
        if new_device_name != old_device_name:
            _LOGGER.debug(
                "Adjusting device name from %s to %s",
                old_device_name,
                new_device_name,
            )

            # Update entity name in device registry
            device_registry = dr.async_get(self.hass)
            device_registry.async_update_device(
                self.registry_entry.device_id,
                name=new_device_name,
            )

        # Get old entity id
        old_entity_id = self.entity_id.split(".", 1)[1]

        # Create entity id base from host
        new_entity_id = self.api_device.host

        # Append entity port name (port id or label) to entity id
        if self.has_api_entity:
            if self.api_entity.label:
                new_entity_id += f" {self.api_entity.label}"
            else:
                new_entity_id += f" port {self.api_entity.port}"

        # Append entity name (if any) to entity id
        if self.name is not None:
            new_entity_id += f" {self.name}"
        new_entity_id = slugify(new_entity_id)

        # Adjust entity id
        if new_entity_id != old_entity_id:
            _LOGGER.debug(
                "Adjusting entity id from %s to %s",
                old_entity_id,
                new_entity_id,
            )

            # Update entity id in entity registry
            entity_registry = er.async_get(self.hass)
            try:
                new_entity_id = f"{self.domain}.{new_entity_id}"
                entity_registry.async_update_entity(
                    self.entity_id,
                    new_entity_id=new_entity_id,
                )
            except ValueError:
                new_entity_id = entity_registry.async_generate_entity_id(
                    self.domain, new_entity_id
                )
                entity_registry.async_update_entity(
                    self.entity_id,
                    new_entity_id=new_entity_id,
                )

        # Update attributes
        self._handle_attr_update()

        # Write state
        try:
            self.async_write_ha_state()
        except RuntimeError:
            _LOGGER.error(
                "Update attempt failed for entity %s, skipping update",
                self.unique_id,
            )
            return

    def _handle_attr_update(self) -> None:
        """Handle (optional) attribute updates from API data."""
        pass

    async def async_update(self) -> None:
        """Update data for this entity by request."""
        # Update directly via API
        if self.has_api_entity:
            await self.api_entity.update()
        else:
            await self.api_device.update()

        # Update attributes
        self._handle_attr_update()
