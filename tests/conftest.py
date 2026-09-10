"""Fixtures for SMA ennexOS Cloud tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sma_ennexos_cloud.const import (
    CONF_ENERGY_POLL_INTERVAL,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENERGY_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="SMA Solar Plant",
        data={
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "password123",
        },
        options={
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
            CONF_ENERGY_POLL_INTERVAL: DEFAULT_ENERGY_POLL_INTERVAL,
        },
        entry_id="sma_test_entry_id",
        unique_id="user@example.com",
    )


@pytest.fixture
def mock_sma_client() -> Generator[MagicMock]:
    """Patch SmaClient."""
    with patch("sma_ennexos_cloud.SmaClient") as mock_cls:
        client = MagicMock()
        client.login.return_value = True
        client.close.return_value = None
        client.get_live_measurements.return_value = {
            "Power_Total": 4500.0,
            "Grid_Feed_In": 3200.0,
        }
        client.get_plants.return_value = [
            {"plantId": "plant_1", "name": "SMA Solar Plant"}
        ]
        mock_cls.return_value = client
        yield client
