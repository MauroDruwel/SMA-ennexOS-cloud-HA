"""DataUpdateCoordinator for SMA ennexOS Cloud."""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ENERGY_POLL_INTERVAL,
    CONF_PASSWORD,
    CONF_PLANT_ID,
    CONF_PLANT_NAME,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENERGY_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Maximum number of re-login attempts per poll cycle before giving up.
_MAX_RELOGIN_ATTEMPTS = 2


class SmaEnnexosCloudDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches live power and daily energy from SMA ennexOS."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client) -> None:
        self.entry = entry
        self.client = client
        self._last_energy_poll = 0.0
        self._last_daily_wh: int | None = None
        self._plant_name: str | None = entry.data.get(CONF_PLANT_NAME)

        poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def update_poll_interval(self) -> None:
        """Re-apply the poll interval from current options (call after options update)."""
        self.update_interval = timedelta(
            seconds=self.entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        )

    # ------------------------------------------------------------------
    # DataUpdateCoordinator hooks
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self._fetch_data)
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error fetching SMA ennexOS data: {err}") from err

    # ------------------------------------------------------------------
    # Synchronous fetch (runs in executor)
    # ------------------------------------------------------------------

    def _fetch_data(self) -> dict:
        """Fetch power + energy, re-authenticating on session expiry."""
        for attempt in range(_MAX_RELOGIN_ATTEMPTS):
            try:
                return self._do_fetch()
            except Exception as err:
                err_str = str(err).lower()
                session_expired = any(
                    kw in err_str
                    for kw in ("401", "unauthorized", "token", "expired", "login")
                )
                if session_expired and attempt < _MAX_RELOGIN_ATTEMPTS - 1:
                    _LOGGER.warning(
                        "SMA session appears expired (%s); re-authenticating (attempt %d/%d)",
                        err,
                        attempt + 1,
                        _MAX_RELOGIN_ATTEMPTS,
                    )
                    self._relogin()
                    # Reset energy poll timer so we refresh energy after re-auth too
                    self._last_energy_poll = 0.0
                else:
                    raise UpdateFailed(
                        f"Error fetching SMA ennexOS data: {err}"
                    ) from err

        # Should not be reached, but satisfy the type checker.
        raise UpdateFailed("Unexpected error in SMA data fetch loop")

    def _do_fetch(self) -> dict:
        """Perform the actual API calls (may raise if session is invalid)."""
        now = time.monotonic()
        energy_poll_interval = self.entry.options.get(
            CONF_ENERGY_POLL_INTERVAL, DEFAULT_ENERGY_POLL_INTERVAL
        )

        # --- Live power ---
        try:
            power = self.client.get_current_power()
            power_val = power.value
            power_ts = power.timestamp
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Could not read current power: %s", err)
            power_val = None
            power_ts = ""

        # --- Plant name (once) ---
        if self._plant_name is None:
            try:
                self._plant_name = self.client.get_plant_name()
            except Exception:  # noqa: BLE001
                self._plant_name = self.entry.data.get(CONF_PLANT_NAME, "SMA Plant")

        # --- Daily energy (throttled) ---
        if now - self._last_energy_poll >= energy_poll_interval:
            try:
                energy = self.client.get_daily_energy()
                self._last_daily_wh = energy.wh
                self._last_energy_poll = now
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Could not read daily energy: %s", err)

        return {
            "power": power_val,
            "power_timestamp": power_ts,
            "daily_wh": self._last_daily_wh,
            "plant_name": self._plant_name,
        }

    def _relogin(self) -> None:
        """Force a fresh login, replacing the client's session."""
        from sma_ennexos_cloud import SmaClient

        try:
            self.client.close()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Error closing client before relogin: %s", err)

        self.client = SmaClient(
            username=self.entry.data[CONF_USERNAME],
            password=self.entry.data[CONF_PASSWORD],
            component_id=self.entry.data.get(CONF_PLANT_ID),
        )
        self.client.login()
        _LOGGER.info("SMA ennexOS: re-authentication successful")
