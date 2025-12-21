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
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import EntityCategory
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
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ubiquiti mFi mPower sensors based on config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
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
        MPowerHostSensorEntity(coordinator),
        MPowerIPSensorEntity(coordinator),
        MPowerInterfaceSensorEntity(coordinator),
        MPowerPortsSensorEntity(coordinator),
        MPowerPollSensorEntity(coordinator),
        *[MPowerPowerSensorEntity(coordinator, e) for e in api_entities],
        *[MPowerCurrentSensorEntity(coordinator, e) for e in api_entities],
        *[MPowerVoltageSensorEntity(coordinator, e) for e in api_entities],
        *[MPowerPowerFactorSensorEntity(coordinator, e) for e in api_entities],
        *[MPowerEnergySensorEntity(coordinator, e) for e in api_entities],
    ]

    await coordinator.async_migrate_old_entity_unique_ids(entities)

    return entities


class MPowerSensorEntity(MPowerCoordinatorEntity, SensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower sensors."""

    domain: str = sensor.DOMAIN


class MPowerHostSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower host sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:dns"
    _attr_translation_key = "host"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the host sensor."""
        return f"{self.api_device.unique_id}-host"

    @property
    def native_value(self) -> str:
        """Return the native value of the host sensor."""
        return self.api_device.host


class MPowerIPSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower IP sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:ip"
    _attr_translation_key = "ipaddr"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the IP sensor."""
        return f"{self.api_device.unique_id}-ipaddr"

    @property
    def native_value(self) -> str:
        """Return the native value of the IP sensor."""
        return self.api_device.ipaddr


class MPowerInterfaceSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower interface sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "iface"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the interface sensor."""
        return f"{self.api_device.unique_id}-iface"

    @property
    def icon(self) -> str | None:
        """Return the icon of the interface sensor."""
        if self.api_device.iface == "lan":
            return "mdi:lan"
        return "mdi:wifi"

    @property
    def native_value(self) -> str:
        """Return the native value of the interface sensor."""
        return self.api_device.iface


class MPowerPortsSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower ports sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "ports"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the ports sensor."""
        return f"{self.api_device.unique_id}-ports"

    @property
    def icon(self) -> str | None:
        """Return the icon of the ports sensor."""
        if self.api_device.eu_model:
            return "mdi:power-socket-de"
        return "mdi:power-socket-us"

    @property
    def native_value(self) -> str:
        """Return the native value of the ports sensor."""
        return self.api_device.ports


class MPowerPollSensorEntity(MPowerSensorEntity):
    """Coordinated sensor entity for Ubiquiti mFi mPower poll sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:update"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_translation_key = "poll"

    @property
    def unique_id(self) -> str:
        """Return the unique id of the poll sensor."""
        return f"{self.api_device.unique_id}-poll"

    @property
    def native_value(self) -> str:
        """Return the native value of the poll sensor."""
        return self.coordinator.update_interval.total_seconds()


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
    def native_value(self) -> float | None:
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
    def native_value(self) -> float | None:
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
    def native_value(self) -> float | None:
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
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return 100 * self.api_entity.powerfactor


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
    def native_value(self) -> float | None:
        """Return the native value of the sensor."""
        return self.api_entity.energy / 1000
