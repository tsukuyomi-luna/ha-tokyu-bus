import importlib.util
import unittest
from datetime import UTC
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "model", Path(__file__).parents[1] / "custom_components/tokyu_bus/model.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ModelTests(unittest.TestCase):
    def row(self, **kw):
        return dict(
            route_code="123",
            stop_pole_number="a",
            updown="DOWN",
            time_left=4,
            car_code="1",
            trip_round_number=1,
            congestion_level="HIGH",
            **kw,
        )

    def test_valid(self):
        self.assertEqual(
            m.normalize({"approaching_to": [self.row()]}, "123", "a", "DOWN")[0][
                "congestion_level"
            ],
            "HIGH",
        )

    def test_filters(self):
        for key, value in [
            ("route_code", "2"),
            ("stop_pole_number", "b"),
            ("updown", "UP"),
            ("time_left", -1),
            ("time_left", True),
        ]:
            r = self.row()
            r[key] = value
            self.assertEqual(
                m.normalize({"approaching_to": [r]}, "123", "a", "DOWN"), []
            )

    def test_round_not_collapsed(self):
        r = self.row()
        r["trip_round_number"] = 2
        self.assertEqual(
            len(m.normalize({"approaching_to": [self.row(), r]}, "123", "a", "DOWN")), 2
        )

    def test_unknown(self):
        r = self.row()
        r["congestion_level"] = "NEW"
        self.assertEqual(
            m.normalize({"approaching_to": [r]}, "123", "a", "DOWN")[0][
                "congestion_level"
            ],
            "UNKNOWN",
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            m.normalize({}, "123", "a", "DOWN")

    def test_empty(self):
        self.assertEqual(m.normalize({"approaching_to": []}, "123", "a", "DOWN"), [])


if __name__ == "__main__":
    unittest.main()


class TimetableTests(unittest.TestCase):
    def test_previous_service_day(self):
        from datetime import date, datetime
        from zoneinfo import ZoneInfo

        now = datetime(2026, 9, 30, 0, 30, tzinfo=ZoneInfo("Asia/Tokyo"))
        tables = [
            (date(2026, 9, 29), [{"route_code": "123", "departure_time": "25:00"}])
        ]
        self.assertEqual(m.next_departure(tables, now, "123").hour, 1)

    def test_invalid_and_past(self):
        from datetime import date, datetime

        now = datetime(2026, 9, 29, 22, 0, tzinfo=UTC)
        rows = [
            {"route_code": "123", "departure_time": t}
            for t in ["21:00", "22:99", "48:00", "bad"]
        ]
        self.assertIsNone(m.next_departure([(date(2026, 9, 29), rows)], now, "123"))


class RemainingTests(unittest.TestCase):
    def stop(self, code, order, status, kind="OTHER"):
        return {
            "stop": {"code": code},
            "stop_order": order,
            "status": status,
            "type": kind,
        }

    def test_count_includes_boarding(self):
        rows = [self.stop("a", 4, "NEXT"), self.stop("b", 5, "UNPASSED", "FROM")]
        self.assertEqual(m.stops_remaining(rows, "b"), 2)
        self.assertEqual(m.stops_remaining(rows[1:], "b"), None)
        rows[1]["status"] = "NEXT"
        self.assertEqual(m.stops_remaining(rows[1:], "b"), 1)

    def test_loop_ambiguity_and_missing(self):
        rows = [
            self.stop("b", 1, "NEXT", "FROM"),
            self.stop("b", 2, "UNPASSED", "FROM"),
        ]
        self.assertIsNone(m.stops_remaining(rows, "b"))
        rows[0]["status"] = "PASSED"
        rows[1]["status"] = "NEXT"
        self.assertEqual(m.stops_remaining(rows, "b"), 1)
        self.assertIsNone(m.stops_remaining(None, "b"))

    def test_gapped_order(self):
        rows = [self.stop("a", 1, "NEXT"), self.stop("b", 3, "UNPASSED", "FROM")]
        self.assertIsNone(m.stops_remaining(rows, "b"))

    def test_exact_departure_rolls_forward(self):
        from datetime import datetime

        now = datetime(2026, 9, 30, 8, 10, tzinfo=UTC)
        rows = [
            {"route_code": "123", "departure_time": t}
            for t in ["08:00", "08:10", "08:20"]
        ]
        previous, following = m.departure_window([(now.date(), rows)], now, "123")
        self.assertEqual(previous.minute, 10)
        self.assertEqual(following.minute, 20)
