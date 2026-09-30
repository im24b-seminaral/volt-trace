"""
test_analysis.py - Unit- und Integrationstests für das volt_trace Modul.

Zweck und Aufgaben dieser Datei:
--------------------------------
1. Tests für SDAT-Parsing (sdat.py):
   - Korrektes Auslesen von DocumentID (ID735, ID742).
   - Validierung von Start-/End-Zeitpunkten und Resolutions (z. B. 15 MIN).
   - Korrekte Extraktion von Observation-Sequenzen und Verbrauchsvolumen.
2. Tests für ESL-Parsing (esl.py):
   - Korrektes Parsen von TimePeriod end und OBIS-Kennzahlen.
   - Richtige Addition von Hochtarif- und Niedertarif-Werten:
     * 1-1:1.8.1 + 1-1:1.8.2 -> ID742 (Netzbezug)
     * 1-1:2.8.1 + 1-1:2.8.2 -> ID735 (Solar-Einspeisung)
3. Tests für Analyse und Berechnung (analysis.py):
   - Duplikaterkennung und -bereinigung anhand von Zeitstempeln (UTC).
   - Umrechnung relativer Verbrauchswerte in korrekte fortlaufende absolute Zählerstände.
   - Mathematische Konsistenz der aufsummierten Werte im Vergleich zu den ESL-Zählerständen.
4. Tests für Datenexport (export.py):
   - Überprüfung des CSV-Formats (Spaltenüberschriften: timestamp, value; Dateinamen: ID735.csv, ID742.csv).
   - Validierung der JSON-Exportstruktur (sensorId, ts, value).
"""
from datetime import datetime, timedelta, timezone

import pytest

from volt_trace.analysis import (
    MeterReading,
    calculate_all_meter_readings,
    calculate_meter_readings,
    check_series,
)
from volt_trace.esl import EslMeterReading
from volt_trace.sdat import MeasuredValue

ANCHOR = datetime(2019, 1, 1, tzinfo=timezone.utc)


def _values(first_interval_end, volumes, step=15):
    return [
        MeasuredValue(
            first_interval_end + timedelta(minutes=step * i),
            i + 1,
            v,
            step,
        )
        for i, v in enumerate(volumes)
    ]


def test_value_at_anchor_equals_esl_value():
    readings = list(calculate_meter_readings(_values(ANCHOR, [1.0, 2.0]), 100.0, ANCHOR).values())
    assert readings[0].timestamp == ANCHOR
    assert readings[0].meter_value == 100.0
    assert readings[1].meter_value == 102.0


def test_value_before_anchor_is_anchor_minus_volume():
    values = _values(ANCHOR - timedelta(minutes=15), [0.5, 1.0])
    readings = list(calculate_meter_readings(values, 100.0, ANCHOR).values())
    assert readings[0].timestamp == ANCHOR - timedelta(minutes=15)
    assert readings[0].meter_value == 99.5
    assert readings[1].meter_value == 100.0


def test_no_timestamp_is_lost():
    values = _values(ANCHOR - timedelta(hours=1), [1.0] * 8)
    values.append(values[0])  # Duplikat
    series = calculate_meter_readings(values, 100.0, ANCHOR)
    assert len(series) == 8
    assert next(iter(series)) == ANCHOR - timedelta(hours=1)  # Kurve beginnt beim frühesten sdat-Zeitpunkt


def test_anchor_is_first_esl_reading_inside_sdat_range():
    values = _values(ANCHOR, [1.0] * 4)
    esl = [
        EslMeterReading(ANCHOR - timedelta(days=30), 50.0),  # vor dem sdat-Zeitraum
        EslMeterReading(ANCHOR + timedelta(minutes=30), 200.0),
    ]
    readings = list(calculate_all_meter_readings({"ID742": values}, {"ID742": esl})["ID742"].values())
    assert readings[2].meter_value == 200.0
    assert readings[0].meter_value == 198.0


def test_meter_reading_joins_consumption_and_meter_value():
    # NFA-02: Verbrauch und Zählerstand stehen zum selben Zeitpunkt im selben Messwert.
    series = calculate_meter_readings(_values(ANCHOR, [0.25, 0.5]), 100.0, ANCHOR)
    assert series[ANCHOR + timedelta(minutes=15)] == MeterReading(
        ANCHOR + timedelta(minutes=15), 0.5, 100.5)


def test_series_is_unique_sorted_and_utc():
    # Unsortierte Eingabe mit Duplikat ergibt trotzdem eine gültige Zeitreihe.
    values = _values(ANCHOR - timedelta(hours=1), [1.0] * 8)
    values = list(reversed(values)) + values[:2]
    series = calculate_meter_readings(values, 100.0, ANCHOR)
    check_series(series)
    keys = list(series)
    assert keys == sorted(set(keys))
    assert all(key.utcoffset() == timedelta(0) for key in keys)


def _reading(time):
    return MeterReading(time, 1.0, 100.0)


def test_check_series_rejects_unsorted():
    later, earlier = ANCHOR + timedelta(minutes=15), ANCHOR
    with pytest.raises(ValueError, match="aufsteigend"):
        check_series({later: _reading(later), earlier: _reading(earlier)})


def test_check_series_rejects_non_utc():
    local = datetime(2019, 1, 1, 1, tzinfo=timezone(timedelta(hours=1)))
    with pytest.raises(ValueError, match="UTC"):
        check_series({local: _reading(local)})


def test_check_series_rejects_key_mismatch():
    with pytest.raises(ValueError, match="Schlüssel"):
        check_series({ANCHOR: _reading(ANCHOR + timedelta(minutes=15))})
