"""Support for Ubiquiti mFi mPower sensors."""

from __future__ import annotations

from homeassistant.components import sensor
from homeassistant.components.sensor import (
    SensorStateClass,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import api
from .config_flow import create_schema
from .const import DOMAIN
from .update_coordinator import MPowerCoordinatorEntity, MPowerDataUpdateCoordinator

PLATFORM_SCHEMA = sensor.PLATFORM_SCHEMA.extend(create_schema().schema)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Ubiquiti mFi mPower sensors based on config."""
    coordinator = await api.create_coordinator(hass, config[DOMAIN])
    entities = await async_create_entities(coordinator)
    async_add_entities(entities, False)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubiquiti mFi mPower sensors based on config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = await async_create_entities(coordinator)
    async_add_entities(entities, False)


async def async_create_entities(
    coordinator: MPowerDataUpdateCoordinator,
) -> list[MPowerSensorEntity]:
    """Create sensor entities from Ubiquiti mFi mPower sensors."""
    api_device = coordinator.api_device

    try:
        api_entities: list[api.MPowerSensor] = await api_device.create_sensors()
    except Exception as exc:
        raise PlatformNotReady from exc

    entities: list[MPowerSensorEntity] = [
        *[MPowerPowerSensorEntity(e, coordinator) for e in api_entities],
        *[MPowerCurrentSensorEntity(e, coordinator) for e in api_entities],
        *[MPowerVoltageSensorEntity(e, coordinator) for e in api_entities],
        *[MPowerPowerFactorSensorEntity(e, coordinator) for e in api_entities],
        *[MPowerEnergySensorEntity(e, coordinator) for e in api_entities],
    ]

    return entities


class MPowerSensorEntity(MPowerCoordinatorEntity, SensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower sensors."""

    domain: str = sensor.DOMAIN


class MPowerPowerSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower power sensors."""

    api_entity: api.MPowerSensor

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_translation_key = "power"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the sensor."""
        return f"{self.api_entity.unique_id}-power"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.api_entity.power


class MPowerCurrentSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower current sensors."""

    api_entity: api.MPowerSensor

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "current"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the sensor."""
        return f"{self.api_entity.unique_id}-current"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.api_entity.current


class MPowerVoltageSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower voltage sensors."""

    api_entity: api.MPowerSensor

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_translation_key = "voltage"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the sensor."""
        return f"{self.api_entity.unique_id}-voltage"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.api_entity.voltage


class MPowerPowerFactorSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower power factor sensors."""

    api_entity: api.MPowerSensor

    _attr_device_class = SensorDeviceClass.POWER_FACTOR
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_translation_key = "powerfactor"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the sensor."""
        return f"{self.api_entity.unique_id}-powerfactor"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.api_entity.powerfactor


class MPowerEnergySensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower energy sensors."""

    api_entity: api.MPowerSensor

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_suggested_display_precision = 2
    _attr_translation_key = "energy"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the sensor."""
        return f"{self.api_entity.unique_id}-energy"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.api_entity.energy
