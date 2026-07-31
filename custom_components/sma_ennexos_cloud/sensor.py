from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import SmaEnnexosCloudDataUpdateCoordinator

if TYPE_CHECKING:
    from . import SmaEnnexosConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmaEnnexosConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        SmaEnnexosPowerSensor(coordinator, entry),
        SmaEnnexosDailyEnergySensor(coordinator, entry),
        SmaEnnexosPlantNameSensor(coordinator, entry),
        SmaEnnexosLastSyncSensor(coordinator, entry),
    ]

    async_add_entities(entities)


def get_plant_device_info(coordinator: SmaEnnexosCloudDataUpdateCoordinator, entry: ConfigEntry) -> DeviceInfo:
    plant_name = coordinator.data.get("plant_name", "SMA Plant")
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_plant")},
        name=plant_name,
        manufacturer="SMA",
        model="Sunny Portal / ennexOS",
        configuration_url="https://ennexos.sunnyportal.com/",
    )


class SmaEnnexosBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmaEnnexosCloudDataUpdateCoordinator,
        entry: SmaEnnexosConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry


class SmaEnnexosPowerSensor(SmaEnnexosBaseSensor):
    _attr_name = "Current power"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:solar-power"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_power"
        self._attr_device_info = get_plant_device_info(coordinator, entry)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("power")


class SmaEnnexosDailyEnergySensor(SmaEnnexosBaseSensor):
    _attr_name = "Daily energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_daily_energy"
        self._attr_device_info = get_plant_device_info(coordinator, entry)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("daily_wh")

    @property
    def last_reset(self) -> datetime | None:
        return dt_util.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


class SmaEnnexosPlantNameSensor(SmaEnnexosBaseSensor):
    _attr_name = "Plant name"
    _attr_icon = "mdi:solar-panel"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_plant_name"
        self._attr_device_info = get_plant_device_info(coordinator, entry)

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("plant_name")


class SmaEnnexosLastSyncSensor(SmaEnnexosBaseSensor):
    _attr_name = "Last sync"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:sync"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_sync"
        self._attr_device_info = get_plant_device_info(coordinator, entry)

    @property
    def native_value(self) -> datetime | None:
        timestamp_str = self.coordinator.data.get("power_timestamp")
        if not timestamp_str:
            return None
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
