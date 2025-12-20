"""Update coordinator helpers for the Ubiquiti mFi mPower integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

import async_timeout
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
from .const import DEFAULT_TIMEOUT, DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)


class MPowerDataUpdateCoordinator(DataUpdateCoordinator):
    """Ubiquiti mFi mPower data update coordinator."""

    def __init__(
        self, hass: HomeAssistant, device: api.MPowerDevice, scan_interval: float
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{NAME} {device.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self._api_device = device

    async def _async_update_data(self) -> list[dict]:
        """Fetch data from the device."""
        try:
            updated = self.api_device.updated
            timeout = DEFAULT_TIMEOUT if updated else SLOW_SETUP_MAX_WAIT
            async with async_timeout.timeout(timeout):
                await api.update_device(self.api_device)
        except asyncio.TimeoutError as exc:
            raise asyncio.TimeoutError(exc) from exc
        except api.MPowerAuthenticationError as exc:
            raise ConfigEntryAuthFailed(exc) from exc
        except Exception as exc:
            raise UpdateFailed(exc) from exc

        return self.api_device.data.get("ports", [])

    @property
    def api_device(self) -> api.MPowerDevice:
        """Return the mFi mPower device from the coordinator."""
        return self._api_device


class MPowerCoordinatorEntity(CoordinatorEntity):
    """Coordinator entity baseclass for Ubiquiti mFi mPower entities."""

    api_entity: api.MPowerEntity
    api_device: api.MPowerDevice

    domain: str | None = None

    _attr_assumed_state = False
    _attr_has_entity_name = True

    def __init__(
        self, api_entity: api.MPowerEntity, coordinator: MPowerDataUpdateCoordinator
    ) -> None:
        """Initialize the entity."""
        self.api_entity = api_entity
        self.api_device = api_entity.device
        self.api_label = None

        super().__init__(coordinator)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data

        if data is not None:
            self.api_entity._data = data[self.api_entity.port - 1]

            # Check if api entity label has changed
            if self.api_entity.label != self.api_label:
                # Adjust device name
                device_registry = dr.async_get(self.hass)
                device_registry.async_update_device(
                    self.registry_entry.device_id,
                    name=self.device_name,
                )

                # Adjust entity id
                assert self.domain is not None
                entity_registry = er.async_get(self.hass)
                if self.name is None:
                    new_object_id = slugify(f"{self.device_name}")
                else:
                    new_object_id = slugify(f"{self.device_name} {self.name}")
                try:
                    new_entity_id = f"{self.domain}.{new_object_id}"
                    entity_registry.async_update_entity(
                        self.entity_id,
                        new_entity_id=new_entity_id,
                    )
                except ValueError:
                    new_entity_id = entity_registry.async_generate_entity_id(
                        self.domain, new_object_id
                    )
                    entity_registry.async_update_entity(
                        self.entity_id,
                        new_entity_id=new_entity_id,
                    )

                # Update api label
                self.api_label = self.api_entity.label

            self.async_write_ha_state()

    @property
    def device_name(self) -> str:
        """Return the device name of the entity."""
        if self.api_entity.label:
            return self.api_entity.label
        return f"{self.api_device.name} port {self.api_entity.port}"

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.api_entity.unique_id)},
            name=self.device_name,
            manufacturer=self.api_device.manufacturer,
            model=f"{self.api_device.model} Port {self.api_entity.port}",
            via_device=(DOMAIN, self.api_device.unique_id),
        )
