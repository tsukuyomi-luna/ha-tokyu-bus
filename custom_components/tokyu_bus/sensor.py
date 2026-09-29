"""Approach estimates are not scheduled departure timestamps."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            BusSensor(coordinator, entry, key, label)
            for key, label in [
                ("time_left", "Arrival estimate"),
                ("congestion_level", "Congestion"),
                ("next_stop", "Next stop"),
                ("stops_remaining", "Stops remaining"),
                ("scheduled_departure", "Scheduled departure"),
            ]
        ]
    )


class BusSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:bus"
    _unrecorded_attributes = frozenset({"buses", "stops", "retrieved_at"})

    def __init__(self, coordinator, entry, key, label):
        super().__init__(coordinator)
        self.key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = label
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Community",
        }
        if key == "scheduled_departure":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        if key == "time_left":
            self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self):
        if self.key in ("scheduled_departure", "stops_remaining"):
            return self.coordinator.data.get(self.key)
        if self.key == "next_stop":
            stops = self.coordinator.data.get("stops") or []
            return next(
                (
                    row.get("stop", {}).get("name")
                    for row in stops
                    if row.get("status") == "NEXT"
                ),
                None,
            )
        buses = self.coordinator.data["buses"]
        return buses[0].get(self.key) if buses else None

    @property
    def extra_state_attributes(self):
        return self.coordinator.data
