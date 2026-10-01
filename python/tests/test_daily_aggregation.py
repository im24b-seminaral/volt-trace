"""Tests für die Tagesaggregation nach lokaler Mitternacht Europe/Zurich (NFA-05 / FA-05)."""
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
import pytest
from volt_trace import cli

from volt_trace.cli import _aggregate_by_day, _consumption_day_bucket


def _quarter_hour_ends(first_end, count):
    """SDAT-Zeitstempel = Intervallende (15-Minuten-Schritte)."""
    return [(first_end + timedelta(minutes=15 * i), 1.0) for i in range(count)]


def test_midnight_interval_end_buckets_to_previous_day():
    # 15.01.2024 00:00 Europe/Zurich = 14.01.2024 23:00 UTC (Winter)
    midnight_end = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
    assert _consumption_day_bucket(midnight_end).isoformat() == "2024-01-14"
    afternoon = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert _consumption_day_bucket(afternoon).isoformat() == "2024-01-15"


def _counts(day_bucket_utc, hours):
    # Erstes Intervallende zwei Stunden vor dem Tages-Bucket-UTC, genug Rand für den Tag.
    first_end = day_bucket_utc - timedelta(hours=2) + timedelta(minutes=15)
    points = _quarter_hour_ends(first_end, (hours + 4) * 4)
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
    bucket = datetime(2024, 1, 14, 23, tzinfo=timezone.utc)
    points = _quarter_hour_ends(bucket - timedelta(hours=2) + timedelta(minutes=15), 96)
    for ts, _ in _aggregate_by_day(points, "consumption"):
        assert ts.utcoffset() == timedelta(0)
        assert ts.isoformat().endswith("+00:00")


@pytest.mark.parametrize("start,hours", [
    (datetime(2024, 1, 14, 23, tzinfo=timezone.utc), 24),
    (datetime(2024, 3, 30, 23, tzinfo=timezone.utc), 23),
    (datetime(2024, 10, 26, 22, tzinfo=timezone.utc), 25),
])
def test_date_filter_includes_last_interval_once(start, hours, monkeypatch, capsys):
    end = start + timedelta(hours=hours)
    points = [SimpleNamespace(timestamp=t, volume=v) for t, v in
              _quarter_hour_ends(start, hours * 4 + 2)]
    monkeypatch.setattr(cli, "_load", lambda _: ({"ID742": points}, {}, []))
    cli.cmd_series("unused", "ID742", "consumption", "15min", start.isoformat(), end.isoformat())
    result = json.loads(capsys.readouterr().out)[0]["data"]
    assert len(result) == hours * 4
    assert result[-1]["ts"] == end.isoformat()
    cli.cmd_series("unused", "ID742", "consumption", "day", start.isoformat(), end.isoformat())
    assert json.loads(capsys.readouterr().out)[0]["data"] == [{"ts": start.isoformat(), "value": hours * 4}]
