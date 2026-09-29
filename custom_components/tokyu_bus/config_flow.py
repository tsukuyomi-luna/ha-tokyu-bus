"""Advanced initial setup using explicitly selected route and boarding pole."""

import re

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BusApi
from .const import DOMAIN

SCHEMA = vol.Schema(
    {
        vol.Required("name", default="Tokyu Bus"): str,
        vol.Required("from_stop"): str,
        vol.Required("to_stop"): str,
        vol.Required("route"): str,
        vol.Required("pole"): str,
        vol.Required("direction"): vol.In(["UP", "DOWN"]),
        vol.Required("poll_seconds", default=30): vol.All(
            vol.Coerce(int), vol.Range(min=30, max=3600)
        ),
    }
)


class TokyuFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TokyuOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if any(
                not re.fullmatch(r"[0-9]+", user_input[k])
                for k in ("from_stop", "to_stop", "route")
            ) or not re.fullmatch(r"[A-Za-z0-9]+", user_input["pole"]):
                return self.async_show_form(
                    step_id="user", data_schema=SCHEMA, errors={"base": "invalid_codes"}
                )
            await self.async_set_unique_id(
                ":".join(
                    user_input[k]
                    for k in ("from_stop", "to_stop", "route", "pole", "direction")
                )
            )
            self._abort_if_unique_id_configured()
            try:
                await BusApi(async_get_clientsession(self.hass), user_input).running()
            except TimeoutError, aiohttp.ClientError, ValueError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input["name"], data=user_input
                )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)


class TokyuOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "poll_seconds",
                        default=self.config_entry.options.get("poll_seconds", 30),
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600))
                }
            ),
        )
