from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .coordinator import SmaEnnexosCloudDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]

type SmaEnnexosConfigEntry = ConfigEntry[SmaEnnexosCloudDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SmaEnnexosConfigEntry) -> bool:
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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmaEnnexosConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _close_client(client):
    try:
        client.close()
    except Exception:
        pass
