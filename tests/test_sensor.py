"""Tests for SMA ennexOS Cloud sensors."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_sensor_setup_and_values(
    hass: HomeAssistant, mock_sma_client: MagicMock, mock_config_entry
) -> None:
    """Test setting up sensors and verifying status values."""
    mock_sma_client.get_live_data_status.return_value = "operational"

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)

    # Check live data status sensor
    live_data_entry = entity_reg.async_get("sensor.sma_solar_plant_live_data_status")
    assert live_data_entry is not None
    assert live_data_entry.entity_category is EntityCategory.DIAGNOSTIC

    state = hass.states.get("sensor.sma_solar_plant_live_data_status")
    assert state is not None
    assert state.state == "operational"
    assert state.attributes.get("icon") == "mdi:check-circle-outline"


async def test_sensor_maintenance_state(
    hass: HomeAssistant, mock_sma_client: MagicMock, mock_config_entry
) -> None:
    """Test sensor states when Live Data is under maintenance."""
    mock_sma_client.get_live_data_status.return_value = "under_maintenance"

    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.sma_solar_plant_live_data_status")
    assert state is not None
    assert state.state == "under_maintenance"
    assert state.attributes.get("icon") == "mdi:wrench"
