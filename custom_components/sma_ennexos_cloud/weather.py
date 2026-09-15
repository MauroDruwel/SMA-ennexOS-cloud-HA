"""Weather platform for SMA ennexOS Cloud."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .sensor import get_plant_device_info

if TYPE_CHECKING:
    from . import SmaEnnexosConfigEntry
    from .coordinator import SmaEnnexosCloudDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmaEnnexosConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SMA ennexOS weather entity."""
    coordinator = entry.runtime_data
    async_add_entities([SmaEnnexosWeather(coordinator, entry)])


class SmaEnnexosWeather(CoordinatorEntity, WeatherEntity):
    """Weather entity representing the PV plant's local weather and forecast."""

    _attr_has_entity_name = True
    _attr_name = "Weather"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(
        self,
        coordinator: SmaEnnexosCloudDataUpdateCoordinator,
        entry: SmaEnnexosConfigEntry,
    ) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_weather"
        self._attr_device_info = get_plant_device_info(coordinator, entry)

    @property
    def condition(self) -> str | None:
        """Return the current weather condition."""
        weather = self.coordinator.data.get("weather")
        if weather and weather.now:
            return weather.now.condition
        return None

    @property
    def native_temperature(self) -> float | None:
        """Return the current temperature."""
        weather = self.coordinator.data.get("weather")
        if weather and weather.now:
            return weather.now.temperature
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return extra state attributes."""
        attrs: dict[str, str | None] = {}
        weather = self.coordinator.data.get("weather")
        if weather:
            if weather.city:
                attrs["city"] = weather.city
            if weather.now and weather.now.description:
                attrs["weather_description"] = weather.now.description
        return attrs

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        weather = self.coordinator.data.get("weather")
        if not weather or not weather.tomorrow:
            return None

        tomorrow = weather.tomorrow
        forecast_entry: Forecast = {
            "datetime": tomorrow.date,
            "condition": tomorrow.condition,
            "native_temperature": tomorrow.max_temperature,
            "native_templow": tomorrow.min_temperature,
        }
        return [forecast_entry]
