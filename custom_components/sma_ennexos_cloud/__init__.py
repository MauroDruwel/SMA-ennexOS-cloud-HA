"""The SMA ennexOS Cloud integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, CONF_USERNAME
from .coordinator import SmaEnnexosCloudDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

type SmaEnnexosConfigEntry = ConfigEntry[SmaEnnexosCloudDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SmaEnnexosConfigEntry) -> bool:
    """Set up SMA ennexOS Cloud from a config entry."""
    from sma_ennexos_cloud import SmaClient

    def _create_client():
        client = SmaClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        )
        client.login()
        return client

    client = await hass.async_add_executor_job(_create_client)

    try:
        coordinator = SmaEnnexosCloudDataUpdateCoordinator(hass, entry, client)
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        _close_client(client)
        raise

    entry.runtime_data = coordinator
    entry.async_on_unload(lambda: _close_client(client))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload when the user changes options (poll intervals) so the coordinator
    # picks up the new update_interval without requiring a full HA restart.
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_update))

    return True


async def _async_reload_on_options_update(
    hass: HomeAssistant, entry: SmaEnnexosConfigEntry
) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SmaEnnexosConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _close_client(client) -> None:
    """Safely close the SMA client connection."""
    try:
        client.close()
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Error closing client: %s", err)
