"""Unofficial Tokyu Bus integration."""

import logging
from datetime import timedelta

import aiohttp
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import BusApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


class BusCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(minutes=entry.data["poll_minutes"]),
        )
        self.api = BusApi(async_get_clientsession(hass), entry.data)

    async def _async_update_data(self):
        try:
            buses = await self.api.running()
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            raise UpdateFailed("Bus service request failed") from err
        tracking = None
        if buses:
            try:
                tracking = await self.api.tracking(buses[0])
            except TimeoutError, aiohttp.ClientError, ValueError:
                _LOGGER.debug("Tracking unavailable; arrival data retained")
        scheduled = None
        try:
            scheduled = await self.api.scheduled()
        except TimeoutError, aiohttp.ClientError, ValueError:
            _LOGGER.debug("Timetable unavailable")
        return {
            "buses": buses,
            "stops": tracking,
            "scheduled_departure": scheduled,
            "retrieved_at": dt_util.utcnow().isoformat(),
        }


async def async_setup_entry(hass, entry):
    coordinator = BusCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False
