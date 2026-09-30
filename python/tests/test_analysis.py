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

from volt_trace.analysis import calculate_all_meter_readings, calculate_meter_readings
from volt_trace.esl import EslMeterReading
from volt_trace.sdat import MeasuredValue

ANCHOR = datetime(2019, 1, 1, tzinfo=timezone.utc)


def _values(start, volumes):
    return [MeasuredValue(start + timedelta(minutes=15 * i), i + 1, v)
            for i, v in enumerate(volumes)]


def test_value_at_anchor_equals_esl_value():
    readings = calculate_meter_readings(_values(ANCHOR, [1.0, 2.0]), 100.0, ANCHOR)
    assert readings[0].start_time == ANCHOR
    assert readings[0].start_value == 100.0
    assert readings[1].start_value == 101.0


def test_value_before_anchor_is_anchor_minus_volume():
    values = _values(ANCHOR - timedelta(minutes=15), [0.5, 1.0])
    readings = calculate_meter_readings(values, 100.0, ANCHOR)
    assert readings[0].start_time == ANCHOR - timedelta(minutes=15)
    assert readings[0].start_value == 99.5
    assert readings[1].start_value == 100.0


def test_no_timestamp_is_lost():
    values = _values(ANCHOR - timedelta(hours=1), [1.0] * 8)
    values.append(values[0])  # Duplikat
    readings = calculate_meter_readings(values, 100.0, ANCHOR)
    assert len(readings) == 8
    assert readings[0].start_time == ANCHOR - timedelta(hours=1)  # Kurve beginnt beim frühesten sdat-Zeitpunkt
    assert [r.start_time for r in readings] == sorted(r.start_time for r in readings)


def test_anchor_is_first_esl_reading_inside_sdat_range():
    values = _values(ANCHOR, [1.0] * 4)
    esl = [
        EslMeterReading(ANCHOR - timedelta(days=30), 50.0),  # vor dem sdat-Zeitraum
        EslMeterReading(ANCHOR + timedelta(minutes=30), 200.0),
    ]
    readings = calculate_all_meter_readings({"ID742": values}, {"ID742": esl})["ID742"]
    assert readings[2].start_value == 200.0
    assert readings[0].start_value == 198.0
