"""Guard the opt-in morning automation and timer payload contract."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_morning_end_and_stop():
    scripts = json.loads((ROOT / "examples/scripts.json").read_text())
    morning = scripts["tokyu_bus_live_morning"]
    assert morning["mode"] == "single"
    loop = morning["sequence"][0]["repeat"]
    gate = loop["while"][0]["value_template"]
    assert "weekday() < 5" in gate
    assert "08:00" in gate and "10:00" in gate
    stop = scripts["tokyu_bus_live_stop"]["sequence"]
    assert "script.tokyu_bus_live_morning" in stop[0]["target"]["entity_id"]
    assert stop[-1]["data"]["data"]["tag"] == "tokyu_bus_morning"


def test_bar_is_independent_of_timer():
    scripts = json.loads((ROOT / "examples/scripts.json").read_text())
    loop = scripts["tokyu_bus_live_morning"]["sequence"][0]["repeat"]["sequence"]
    payload = loop[1]["choose"][0]["sequence"][0]["data"]["data"]
    assert payload["chronometer"] is True
    assert "departure" in payload["when"]
    assert "previous" in payload["progress_max"]
    assert payload["progress_bar_direction"] == "increasing"
    # Remaining seconds shrink; do not invert the fraction a second time.
    assert "as_timestamp(now())" in payload["progress"]
    assert "sensor.tokyu_bus_test_stops_remaining" in payload["critical_text"]
    assert loop[1]["default"][0]["data"]["data"]["chronometer"] is False


def test_start_stop_automation():
    autos = json.loads((ROOT / "examples/morning-automations.json").read_text())
    assert autos[0]["triggers"][0]["at"] == "08:00:00"
    assert autos[1]["triggers"][0]["at"] == "10:00:00"
    assert autos[1]["actions"][-1]["data"]["message"] == "clear_notification"
