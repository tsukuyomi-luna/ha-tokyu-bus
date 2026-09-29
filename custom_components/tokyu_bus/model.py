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


def departure_window(tables, now, route):
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
            candidates.append(stamp)
    future = [stamp for stamp in candidates if stamp > now]
    past = [stamp for stamp in candidates if stamp <= now]
    return (max(past) if past else None, min(future) if future else None)


def next_departure(tables, now, route):
    return departure_window(tables, now, route)[1]


def stops_remaining(stops, boarding_code):
    """Count through boarding; ambiguous loop occurrences stay unknown."""
    if not isinstance(stops, list):
        return None
    next_indices = [i for i, row in enumerate(stops) if row.get("status") == "NEXT"]
    if len(next_indices) != 1:
        return None
    start = next_indices[0]
    targets = [
        i
        for i, row in enumerate(stops)
        if i >= start
        and str(row.get("stop", {}).get("code")) == str(boarding_code)
        and row.get("type") == "FROM"
        and row.get("status") in ("NEXT", "UNPASSED")
    ]
    if len(targets) != 1:
        return None
    end = targets[0]
    segment = stops[start : end + 1]
    orders = [row.get("stop_order") for row in segment]
    if any(not isinstance(n, int) or isinstance(n, bool) for n in orders):
        return None
    if orders != list(range(orders[0], orders[0] + len(orders))):
        return None
    return len(segment)
