"""Tests for SMA ennexOS Cloud weather entity."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_weather_setup_and_values(
    hass: HomeAssistant, mock_sma_client: MagicMock, mock_config_entry
) -> None:
    """Test setting up weather entity and verifying state and forecast."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    weather_entry = entity_reg.async_get("weather.sma_solar_plant_weather")
    assert weather_entry is not None

    state = hass.states.get("weather.sma_solar_plant_weather")
    assert state is not None
    assert state.state == "cloudy"
    assert state.attributes.get("temperature") == 24.0
    assert state.attributes.get("city") == "Tielt"
    assert state.attributes.get("weather_description") == "Cloudy"


async def test_weather_daily_forecast(
    hass: HomeAssistant, mock_sma_client: MagicMock, mock_config_entry
) -> None:
    """Test retrieving daily forecast from weather entity."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    assert coordinator is not None

    from custom_components.sma_ennexos_cloud.weather import SmaEnnexosWeather

    weather_entity = SmaEnnexosWeather(coordinator, mock_config_entry)
    forecast = await weather_entity.async_forecast_daily()
    assert forecast is not None
    assert len(forecast) == 1
    assert forecast[0]["datetime"] == "2026-09-15T22:00:00Z"
    assert forecast[0]["condition"] == "sunny"
    assert forecast[0]["native_temperature"] == 18.0
    assert forecast[0]["native_templow"] == 13.0


async def test_weather_empty_state(
    hass: HomeAssistant, mock_sma_client: MagicMock, mock_config_entry
) -> None:
    """Test weather entity handles empty/None weather data gracefully."""
    mock_sma_client.get_weather.return_value = None

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("weather.sma_solar_plant_weather")
    assert state is not None
    assert state.state == "unknown"

    coordinator = mock_config_entry.runtime_data
    from custom_components.sma_ennexos_cloud.weather import SmaEnnexosWeather

    weather_entity = SmaEnnexosWeather(coordinator, mock_config_entry)
    forecast = await weather_entity.async_forecast_daily()
    assert forecast is None
