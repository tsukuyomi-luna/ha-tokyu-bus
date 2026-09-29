"""Pure response normalization; no guesses about GPS or timetable identity."""

FIELDS = (
    "car_code",
    "dia_code",
    "route_code",
    "route_number",
    "route_name",
    "stop_pole_number",
    "trip_round_number",
    "updown",
    "departure_time",
    "arrival_time",
    "reach_time",
    "time_left",
    "congestion_level",
)


def normalize(payload, route, pole, direction):
    rows = payload.get("approaching_to")
    if not isinstance(rows, list):
        raise ValueError("Missing approaching_to list")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid vehicle row")
        if str(row.get("route_code")) != route:
            continue
        if str(row.get("stop_pole_number")) != pole or row.get("updown") != direction:
            continue
        minutes = row.get("time_left")
        if (
            isinstance(minutes, bool)
            or not isinstance(minutes, (int, float))
            or minutes < 0
        ):
            continue
        item = {key: row.get(key) for key in FIELDS}
        if item["congestion_level"] not in (
            "LOW",
            "NORMAL",
            "HIGH",
            "UNCLEAR",
            "UNKNOWN",
        ):
            item["congestion_level"] = "UNKNOWN"
        result.append(item)
    return sorted(result, key=lambda row: row["time_left"])[:10]


def next_departure(tables, now, route):
    """Select future scheduled time, NOT a match to any tracked vehicle."""
    import re
    from datetime import datetime, time, timedelta

    candidates = []
    for day, rows in tables:
        for row in rows:
            if str(row.get("route_code")) != route:
                continue
            clock = row.get("departure_time", "")
            if not isinstance(clock, str) or not re.fullmatch(r"\d{1,2}:\d{2}", clock):
                continue
            hour, minute = map(int, clock.split(":"))
            if hour > 47 or minute > 59:
                continue
            stamp = datetime.combine(day, time(), tzinfo=now.tzinfo) + timedelta(
                hours=hour, minutes=minute
            )
            if stamp >= now:
                candidates.append(stamp)
    return min(candidates) if candidates else None
