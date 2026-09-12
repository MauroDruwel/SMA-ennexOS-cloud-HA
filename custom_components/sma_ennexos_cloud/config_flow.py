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
    CONF_PLANT_ID,
    CONF_PLANT_NAME,
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

    def __init__(self) -> None:
        """Initialize flow."""
        self._username: str | None = None
        self._password: str | None = None
        self._available_plants: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                from sma_ennexos_cloud import SmaClient
                from sma_ennexos_cloud.exceptions import AuthenticationError

                def _login_and_get_plants():
                    client = SmaClient(username=username, password=password)
                    try:
                        client.login()
                        plants = client.get_plants()
                        return [
                            {"component_id": p.component_id, "name": p.name}
                            for p in plants
                        ]
                    finally:
                        try:
                            client.close()
                        except Exception as err:  # noqa: BLE001
                            _LOGGER.debug("Error closing test client: %s", err)

                plants = await self.hass.async_add_executor_job(_login_and_get_plants)
                if not plants:
                    return self.async_abort(reason="no_plants_found")

                existing_plant_ids = {
                    entry.data[CONF_PLANT_ID]
                    for entry in self._async_current_entries()
                    if CONF_PLANT_ID in entry.data
                }
                available_plants = [
                    p for p in plants if p["component_id"] not in existing_plant_ids
                ]

                if not available_plants:
                    return self.async_abort(reason="already_configured")

                if len(available_plants) == 1:
                    plant = available_plants[0]
                    plant_id = plant["component_id"]
                    plant_name = plant["name"]

                    await self.async_set_unique_id(f"{username}_{plant_id}")
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"SMA ennexOS ({plant_name})",
                        data={
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_PLANT_ID: plant_id,
                            CONF_PLANT_NAME: plant_name,
                        },
                    )

                self._username = username
                self._password = password
                self._available_plants = {
                    p["component_id"]: p["name"] for p in available_plants
                }
                return await self.async_step_plant()

            except AuthenticationError as err:
                _LOGGER.warning("Login authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("Unexpected error during login: %s", err)
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

    async def async_step_plant(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle plant selection when multiple plants are found."""
        if user_input is not None:
            plant_id = user_input[CONF_PLANT_ID]
            plant_name = self._available_plants.get(plant_id, plant_id)

            await self.async_set_unique_id(f"{self._username}_{plant_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"SMA ennexOS ({plant_name})",
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_PLANT_ID: plant_id,
                    CONF_PLANT_NAME: plant_name,
                },
            )

        return self.async_show_form(
            step_id="plant",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PLANT_ID): vol.In(self._available_plants),
                }
            ),
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
