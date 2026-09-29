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
            update_interval=timedelta(seconds=30),
        )
        self.base_interval = entry.options.get(
            "poll_seconds",
            entry.data.get("poll_seconds", entry.data.get("poll_minutes", 5) * 60),
        )
        self.failures = 0
        self.update_interval = timedelta(seconds=self.base_interval)
        self.api = BusApi(async_get_clientsession(hass), entry.data)

    async def _async_update_data(self):
        try:
            buses = await self.api.running()
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            self.failures += 1
            self.update_interval = timedelta(
                seconds=min(900, self.base_interval * 2 ** min(self.failures, 5))
            )
            raise UpdateFailed("Bus service request failed") from err
        self.failures = 0
        self.update_interval = timedelta(seconds=self.base_interval)
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
            "poll_seconds": self.base_interval,
            "retrieved_at": dt_util.utcnow().isoformat(),
        }


async def async_setup_entry(hass, entry):
    coordinator = BusCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False


async def _options_updated(hass, entry):
    """Apply polling changes without restarting Home Assistant."""
    await hass.config_entries.async_reload(entry.entry_id)
