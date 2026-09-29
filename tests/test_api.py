"""Transport, route identity, timetable caching, and calendar regressions."""

from datetime import date, datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

CONFIG = {
    "from_stop": "111",
    "to_stop": "222",
    "route": "123",
    "pole": "a",
    "direction": "DOWN",
}


class Response:
    def __init__(self, payload, error=None):
        self.payload = payload
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def raise_for_status(self):
        if self.error:
            raise self.error

    async def json(self):
        return self.payload


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


async def test_transport_is_single_get(api_module):
    session = Session(Response({"approaching_to": []}))
    client = api_module.BusApi(session, CONFIG)
    assert await client.running() == []
    assert len(session.calls) == 1
    url, request = session.calls[0]
    assert url.endswith("/bus_running")
    assert request["params"]["routes"] == "123"
    assert request["headers"]["User-Agent"] == api_module.USER_AGENT


async def test_invalid_response(api_module):
    client = api_module.BusApi(Session(Response([])), CONFIG)
    with pytest.raises(ValueError, match="Invalid response"):
        await client.running()


async def test_failure_not_retried(api_module):
    session = Session(Response({}, RuntimeError("HTTP failure")))
    with pytest.raises(RuntimeError, match="HTTP failure"):
        await api_module.BusApi(session, CONFIG).running()
    assert len(session.calls) == 1


async def test_missing_tracking_identity_does_not_request(api_module):
    session = Session(Response({}))
    assert await api_module.BusApi(session, CONFIG).tracking({}) is None
    assert session.calls == []


async def test_tracking_preserves_round(api_module):
    session = Session(Response({"schedule": []}))
    bus = {
        "car_code": "car",
        "dia_code": "dia",
        "route_code": "123",
        "updown": "DOWN",
        "trip_round_number": 2,
    }
    assert await api_module.BusApi(session, CONFIG).tracking(bus) == []
    assert session.calls[0][1]["params"]["trip_round_number"] == 2


async def test_cache_expires_on_japan_date_change(api_module):
    clock = [datetime(2026, 9, 29, 12, tzinfo=ZoneInfo("Asia/Tokyo"))]
    client = api_module.BusApi(None, CONFIG, now=lambda: clock[0])
    client.get = AsyncMock(return_value={"timetables": []})
    assert await client.scheduled() is None
    assert await client.scheduled() is None
    assert client.get.await_count == 1
    clock[0] = clock[0].replace(day=30)
    await client.scheduled()
    assert client.get.await_count == 2


async def test_bad_timetable_not_cached(api_module):
    client = api_module.BusApi(None, CONFIG)
    client.get = AsyncMock(return_value={})
    with pytest.raises(ValueError, match="Missing timetables"):
        await client.scheduled()
    assert client._timetables == {}


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 9, 29), "NORMAL"),
        (date(2026, 9, 26), "SATURDAY"),
        (date(2026, 9, 27), "HOLIDAY"),
        (date(2026, 9, 23), "HOLIDAY"),
    ],
)
def test_regular_calendar(api_module, day, expected):
    assert api_module.timetable_kind(day) == expected


async def test_rate_limit_backs_off_without_more_http(api_module):
    import aiohttp

    error = aiohttp.ClientResponseError(
        None, (), status=429, headers={"Retry-After": "600"}
    )
    session = Session(Response({}, error))
    client = api_module.BusApi(session, CONFIG)
    with pytest.raises(aiohttp.ClientResponseError):
        await client.running()
    with pytest.raises(ValueError, match="backed off"):
        await client.running()
    assert len(session.calls) == 1
