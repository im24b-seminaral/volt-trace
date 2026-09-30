"""Tests für die Tagesaggregation nach lokaler Mitternacht Europe/Zurich (NFA-05)."""
from datetime import datetime, timedelta, timezone

from volt_trace.cli import _aggregate_by_day


def _quarter_hours(start, count):
    return [(start + timedelta(minutes=15 * i), 1.0) for i in range(count)]


def _counts(start_utc, hours):
    points = _quarter_hours(start_utc - timedelta(hours=2), (hours + 4) * 4)
    return {ts: value for ts, value in _aggregate_by_day(points, "consumption")}


def test_winter_day_starts_23z():
    result = _counts(datetime(2024, 1, 14, 23, tzinfo=timezone.utc), 24)
    assert result[datetime(2024, 1, 14, 23, tzinfo=timezone.utc)] == 96


def test_summer_day_starts_22z():
    result = _counts(datetime(2024, 7, 14, 22, tzinfo=timezone.utc), 24)
    assert result[datetime(2024, 7, 14, 22, tzinfo=timezone.utc)] == 96


def test_dst_start_has_92_values():
    result = _counts(datetime(2024, 3, 30, 23, tzinfo=timezone.utc), 23)
    assert result[datetime(2024, 3, 30, 23, tzinfo=timezone.utc)] == 92


def test_dst_end_has_100_values():
    result = _counts(datetime(2024, 10, 26, 22, tzinfo=timezone.utc), 25)
    assert result[datetime(2024, 10, 26, 22, tzinfo=timezone.utc)] == 100


def test_bucket_timestamps_are_utc():
    points = _quarter_hours(datetime(2024, 1, 14, 23, tzinfo=timezone.utc), 96)
    for ts, _ in _aggregate_by_day(points, "consumption"):
        assert ts.utcoffset() == timedelta(0)
        assert ts.isoformat().endswith("+00:00")
