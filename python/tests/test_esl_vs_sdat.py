"""Soll-Ist-Vergleich: berechneter Zählerstand vs. ESL-Wert an jedem Stichtag (FA-07 / NFA-04).

Der Anker ist der erste ESL-Stichtag im sdat-Zeitraum, alle weiteren Stichtage im
sdat-Zeitraum sind unabhängige Prüfpunkte. Die Ergebnistabelle landet in
python/export/esl_vs_sdat.csv und kann ins Testprotokoll übernommen werden.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from volt_trace.analysis import DATA_DIR, ESL_TOLERANCE_KWH, compare_with_esl
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
    return result, sdat


def test_every_esl_date_inside_sdat_range_is_checked(comparisons):
    result, sdat = comparisons
    for sensor_id in SENSORS:
        timestamps = [mv.timestamp for mv in sdat[sensor_id]]
        first, last = min(timestamps), max(timestamps)
        rows = [c for c in result if c.sensor_id == sensor_id]
        inside = [c for c in rows if first <= c.time <= last]

        assert sum(c.is_anchor for c in rows) == 1
        assert len(inside) > 1, f"{sensor_id}: keine Prüfpunkte im sdat-Zeitraum"
        # Jeder Stichtag im sdat-Zeitraum braucht einen berechneten Zählerstand.
        assert all(c.calculated_value is not None for c in inside)


def test_meter_readings_match_esl_within_tolerance(comparisons):
    result, _ = comparisons
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


def test_compare_with_esl_flags_anchor_ok_deviation_and_out_of_range():
    t0 = datetime(2019, 1, 1, tzinfo=timezone.utc)
    values = [MeasuredValue(t0 + timedelta(minutes=15 * i), i + 1, 1.0) for i in range(8)]
    esl = [
        EslMeterReading(t0, 100.0),                          # Anker
        EslMeterReading(t0 + timedelta(hours=1), 104.0),     # 4 x 1.0 -> OK
        EslMeterReading(t0 + timedelta(hours=1, minutes=45), 110.0),  # 107 berechnet
        EslMeterReading(t0 + timedelta(days=1), 200.0),      # ausserhalb sdat
    ]
    result = compare_with_esl({"ID742": values}, {"ID742": esl})
    assert [c.status for c in result] == ["Anker", "OK", "Abweichung", "nicht prüfbar"]
    assert result[2].delta == pytest.approx(-3.0)
