"""Tests for the SMA ennexOS Cloud config and options flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.sma_ennexos_cloud.const import (
    CONF_ENERGY_POLL_INTERVAL,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    CONF_PLANT_NAME,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DOMAIN,
)
from sma_ennexos_cloud.models import PlantInfo


async def test_flow_user_single_plant(hass: HomeAssistant) -> None:
    """Test successful single-plant configuration."""
    with patch("sma_ennexos_cloud.SmaClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.login.return_value = True
        mock_client.get_plants.return_value = [
            PlantInfo(component_id="17478443", name="SMA Solar Plant")
        ]
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "new_user@example.com",
                CONF_PASSWORD: "secure_password",
            },
        )
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == "SMA ennexOS (SMA Solar Plant)"
        assert result2["data"][CONF_USERNAME] == "new_user@example.com"
        assert result2["data"][CONF_PLANT_ID] == "17478443"
        assert result2["data"][CONF_PLANT_NAME] == "SMA Solar Plant"


async def test_flow_user_multiple_plants(hass: HomeAssistant) -> None:
    """Test multi-plant selection flow."""
    with patch("sma_ennexos_cloud.SmaClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.login.return_value = True
        mock_client.get_plants.return_value = [
            PlantInfo(component_id="111", name="Plant Alpha"),
            PlantInfo(component_id="222", name="Plant Beta"),
        ]
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "user@example.com",
                CONF_PASSWORD: "password",
            },
        )
        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "plant"

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_PLANT_ID: "222",
            },
        )
        assert result3["type"] is FlowResultType.CREATE_ENTRY
        assert result3["title"] == "SMA ennexOS (Plant Beta)"
        assert result3["data"][CONF_PLANT_ID] == "222"
        assert result3["data"][CONF_PLANT_NAME] == "Plant Beta"


async def test_flow_user_invalid_auth(hass: HomeAssistant) -> None:
    """Test login failure triggers invalid_auth error."""
    with patch("sma_ennexos_cloud.SmaClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.login.side_effect = Exception("401 Unauthorized")
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "wrong@example.com",
                CONF_PASSWORD: "wrong_password",
            },
        )
        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"]["base"] == "invalid_auth"


async def test_flow_user_no_plants(hass: HomeAssistant) -> None:
    """Test abort when no plants found."""
    with patch("sma_ennexos_cloud.SmaClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.login.return_value = True
        mock_client.get_plants.return_value = []
        mock_client_cls.return_value = mock_client

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "empty@example.com",
                CONF_PASSWORD: "password",
            },
        )
        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "no_plants_found"


async def test_options_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """Test modifying poll intervals via options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_POLL_INTERVAL: 45,
            CONF_ENERGY_POLL_INTERVAL: 600,
        },
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_POLL_INTERVAL] == 45
    assert mock_config_entry.options[CONF_ENERGY_POLL_INTERVAL] == 600
