"""Bounded, read-only requests to the undocumented Tokyu app API."""

import asyncio
from collections.abc import Callable, Mapping
from datetime import date, datetime, timedelta
from time import monotonic
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp
import jpholiday

from .model import next_departure, normalize

BASE_URL = "https://api.railway.dp.tokyu.co.jp/v2.1/"
USER_AGENT = (
    "TokyuLine/4.25.0 (jp.co.tokyu.tokyulinesapplication; build:196; Android SDK 36) "
)
JAPAN_TIME = ZoneInfo("Asia/Tokyo")
REQUEST_TIMEOUT_SECONDS = 20


def timetable_kind(day: date) -> str:
    """Use the regular calendar; special operator schedules remain unsupported."""
    if day.weekday() == 6 or jpholiday.is_holiday(day):
        return "HOLIDAY"
    if day.weekday() == 5:
        return "SATURDAY"
    return "NORMAL"


class BusApi:
    """Share transport and a daily timetable cache across one configured route."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        config: Mapping[str, Any],
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.config = config
        self._now = now or (lambda: datetime.now(JAPAN_TIME))
        self._blocked_until: dict[str, float] = {}
        self._cache_date: date | None = None
        self._timetables: dict[str, list[dict[str, Any]]] = {}

    def _route_params(self) -> dict[str, str]:
        return {
            "from_busstop_id": self.config["from_stop"],
            "to_busstop_id": self.config["to_stop"],
            "routes": self.config["route"],
        }

    async def get(self, path: str, params: Mapping[str, Any]) -> dict[str, Any]:
        """Perform one GET without retrying authentication or HTTP failures."""
        if monotonic() < self._blocked_until.get(path, 0):
            raise ValueError("Endpoint temporarily backed off after HTTP failure")
        async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
            async with self.session.get(
                BASE_URL + path,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            ) as response:
                try:
                    response.raise_for_status()
                except aiohttp.ClientResponseError as err:
                    if err.status in (401, 403, 429) or err.status >= 500:
                        retry = (err.headers or {}).get("Retry-After", "")
                        seconds = max(300, int(retry)) if retry.isdigit() else 300
                        self._blocked_until[path] = monotonic() + seconds
                    raise
                data = await response.json()
                if not isinstance(data, dict):
                    raise ValueError("Invalid response object")
                return data

    async def running(self) -> list[dict[str, Any]]:
        """Return matching approaches while preserving direction and trip identity."""
        raw = await self.get("bus_running", self._route_params())
        return normalize(
            raw, self.config["route"], self.config["pole"], self.config["direction"]
        )

    async def tracking(self, bus: Mapping[str, Any]) -> list[dict[str, Any]] | None:
        """Track the exact vehicle, route, direction, and loop iteration."""
        keys = ("car_code", "dia_code", "route_code", "updown", "trip_round_number")
        if any(bus.get(key) in (None, "") for key in keys):
            return None
        data = await self.get(
            "bus_timetable_tracking",
            {
                "from_busstop_id": self.config["from_stop"],
                "to_busstop_id": self.config["to_stop"],
                "car_code": bus["car_code"],
                "busdia_code": bus["dia_code"],
                "busroute_code": bus["route_code"],
                "updown": bus["updown"],
                "trip_round_number": bus["trip_round_number"],
            },
        )
        if not isinstance(data.get("schedule"), list):
            raise ValueError("Missing tracking schedule")
        return data["schedule"]

    async def scheduled(self) -> datetime | None:
        """Select a scheduled departure independently of live vehicle data."""
        now = self._now().astimezone(JAPAN_TIME)
        if self._cache_date != now.date():
            self._timetables.clear()
            self._cache_date = now.date()
        tables = []
        for offset in (-1, 0, 1):
            service_day = now.date() + timedelta(days=offset)
            kind = timetable_kind(service_day)
            if kind not in self._timetables:
                raw = await self.get(
                    "bus_route_timetables",
                    {**self._route_params(), "day_of_week": kind},
                )
                if not isinstance(raw.get("timetables"), list):
                    raise ValueError("Missing timetables list")
                self._timetables[kind] = raw["timetables"]
            tables.append((service_day, self._timetables[kind]))
        return next_departure(tables, now, self.config["route"])
