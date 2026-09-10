"""Config and options flow for SMA ennexOS Cloud."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ENERGY_POLL_INTERVAL,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DEFAULT_ENERGY_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_ENERGY_POLL_INTERVAL,
    MAX_POLL_INTERVAL,
    MIN_ENERGY_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class SmaEnnexosCloudConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for SMA ennexOS Cloud."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()

            try:
                from sma_ennexos_cloud import SmaClient

                def _test_login():
                    client = SmaClient(username=username, password=password)
                    try:
                        client.login()
                        return True
                    except Exception as err:  # noqa: BLE001
                        _LOGGER.warning("Login test failed: %s", err)
                        return False
                    finally:
                        try:
                            client.close()
                        except Exception as err:  # noqa: BLE001
                            _LOGGER.debug("Error closing test client: %s", err)

                result = await self.hass.async_add_executor_job(_test_login)
                if result:
                    return self.async_create_entry(
                        title=f"SMA ennexOS ({username})",
                        data={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        },
                    )
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SmaEnnexosOptionsFlow(config_entry)


class SmaEnnexosOptionsFlow(OptionsFlow):
    """Options flow – lets users change polling intervals without re-entering credentials."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POLL_INTERVAL,
                    default=current.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
                ),
                vol.Optional(
                    CONF_ENERGY_POLL_INTERVAL,
                    default=current.get(
                        CONF_ENERGY_POLL_INTERVAL, DEFAULT_ENERGY_POLL_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(
                        min=MIN_ENERGY_POLL_INTERVAL, max=MAX_ENERGY_POLL_INTERVAL
                    ),
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
