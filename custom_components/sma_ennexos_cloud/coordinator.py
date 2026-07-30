from datetime import timedelta
import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, POLL_INTERVAL, ENERGY_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SmaEnnexosCloudDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client
    ) -> None:
        self.entry = entry
        self.client = client
        self._last_energy_poll = 0.0
        self._last_daily_wh = 0
        self._plant_name = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(
                self._fetch_data
            )
        except Exception as err:
            raise UpdateFailed(f"Error fetching SMA ennexOS data: {err}") from err

    def _fetch_data(self) -> dict:
        from sma_ennexos_cloud import SmaClient

        if not hasattr(self.client, "access_token"):
            self.client = SmaClient(
                username=self.entry.data[CONF_USERNAME],
                password=self.entry.data[CONF_PASSWORD],
            )
            self.client.login()
            self._last_energy_poll = 0.0
            self._last_daily_wh = 0

        now = time.monotonic()

        try:
            power = self.client.get_current_power()
            power_val = power.value
            power_ts = power.timestamp
        except Exception:
            power_val = None
            power_ts = ""

        if self._plant_name is None:
            try:
                self._plant_name = self.client.get_plant_name()
            except Exception:
                self._plant_name = "SMA Plant"

        if now - self._last_energy_poll >= ENERGY_POLL_INTERVAL:
            try:
                energy = self.client.get_daily_energy()
                self._last_daily_wh = energy.wh
                self._last_energy_poll = now
            except Exception:
                pass

        return {
            "power": power_val,
            "power_timestamp": power_ts,
            "daily_wh": self._last_daily_wh,
            "plant_name": self._plant_name,
        }
