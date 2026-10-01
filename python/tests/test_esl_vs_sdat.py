"""Soll-Ist-Vergleich: berechneter Zählerstand vs. ESL-Wert an jedem Stichtag (FA-07 / NFA-04).

Der Anker ist der erste ESL-Stichtag im sdat-Zeitraum, alle weiteren Stichtage im
sdat-Zeitraum sind unabhängige Prüfpunkte. Die Ergebnistabelle landet in
python/export/esl_vs_sdat.csv und kann ins Testprotokoll übernommen werden.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from volt_trace.analysis import (
    DATA_DIR,
    ESL_TOLERANCE_KWH,
    calculate_all_meter_readings,
    check_series,
    compare_with_esl,
)
from volt_trace.esl import EslMeterReading, load_esl_folder
from volt_trace.export import export_esl_comparison_csv
from volt_trace.sdat import MeasuredValue, load_sdat_folder

REPORT_FILE = Path(__file__).resolve().parents[1] / "export" / "esl_vs_sdat.csv"
SENSORS = ("ID735", "ID742")


@pytest.fixture(scope="module")
def comparisons():
    if not (DATA_DIR / "SDAT-Files").is_dir() or not (DATA_DIR / "ESL-Files").is_dir():
        pytest.skip(f"Beispieldaten fehlen in {DATA_DIR}")
    sdat = load_sdat_folder(DATA_DIR / "SDAT-Files")
    esl = load_esl_folder(DATA_DIR / "ESL-Files")
    result = compare_with_esl(sdat, esl)
    export_esl_comparison_csv(result, REPORT_FILE)
    return result, sdat, esl


def test_every_esl_date_inside_sdat_range_is_checked(comparisons):
    result, sdat, _ = comparisons
    for sensor_id in SENSORS:
        timestamps = [mv.timestamp for mv in sdat[sensor_id]]
        first, last = min(timestamps), max(timestamps)
        rows = [c for c in result if c.sensor_id == sensor_id]
        inside = [c for c in rows if first <= c.time <= last]

        assert sum(c.is_anchor for c in rows) == 1
        assert len(inside) > 1, f"{sensor_id}: keine Prüfpunkte im sdat-Zeitraum"
        # Jeder Stichtag im sdat-Zeitraum braucht einen berechneten Zählerstand.
        assert all(c.calculated_value is not None for c in inside)


@pytest.mark.xfail(
    strict=True,
    reason="Known SDAT/ESL discrepancy in the sample data; issue #12 reports it without changing values",
)
def test_meter_readings_match_esl_within_tolerance(comparisons):
    result, _, _ = comparisons
    deviations = [c for c in result if c.status == "Abweichung"]
    report = "\n".join(
        f"{c.time:%Y-%m-%d %H:%M}Z {c.sensor_id}: Soll {c.esl_value:.4f}, "
        f"Ist {c.calculated_value:.4f}, Delta {c.delta:+.4f}"
        for c in deviations
    )
    assert not deviations, (
        f"{len(deviations)} Stichtage weichen um >= {ESL_TOLERANCE_KWH} kWh ab "
        f"(Tabelle: {REPORT_FILE}):\n{report}"
    )


def test_series_invariant_holds_on_sample_data(comparisons):
    # NFA-02: pro Sensor eindeutig, aufsteigend, UTC, ohne verlorene Zeitpunkte.
    _, sdat, esl = comparisons
    for sensor_id, series in calculate_all_meter_readings(sdat, esl).items():
        check_series(series)
        assert len(series) == len({mv.timestamp for mv in sdat[sensor_id]})


def test_compare_with_esl_flags_anchor_ok_deviation_and_out_of_range():
    t0 = datetime(2019, 1, 1, tzinfo=timezone.utc)
    values = [
        MeasuredValue(t0 + timedelta(minutes=15 * (i + 1)), i + 1, 1.0, 15)
        for i in range(8)
    ]
    esl = [
        EslMeterReading(t0 + timedelta(minutes=15), 101.0),
        EslMeterReading(t0 + timedelta(minutes=60), 104.0),
        EslMeterReading(t0 + timedelta(minutes=105), 110.0),
        EslMeterReading(t0 + timedelta(days=1), 200.0),
    ]
    result = compare_with_esl({"ID742": values}, {"ID742": esl})
    assert [c.status for c in result] == ["Anker", "OK", "Abweichung", "nicht prüfbar"]
    assert result[2].delta == pytest.approx(-3.0)
