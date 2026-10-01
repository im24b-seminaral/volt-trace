"""Tests für report.py - Kennzahlen, Hinweise und Sensorzeilen des Importberichts."""

from datetime import datetime, timedelta, timezone

from volt_trace.analysis import MeterReading
from volt_trace.esl import EslDataset, EslMeterReading, EslSource, EslValueRow
from volt_trace.localtime import LOCAL_TZ
from volt_trace.report import build_report
from volt_trace.sdat import MeasuredValue, SdatDataset, SdatSource

QUARTER = timedelta(minutes=15)


def _source(file: str, sensor_id: str = "ID742", resolution_unit: str | None = "MIN",
            interval_minutes: int = 15) -> SdatSource:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return SdatSource(file, f"meter_{sensor_id}", start, start,
                      start + timedelta(minutes=interval_minutes), 15, resolution_unit, "V")


def _day_values(day: str, source: SdatSource) -> list[MeasuredValue]:
    """Ein lokaler Tag voller Viertelstunden; timestamp = Intervallende (FA-05)."""
    start = datetime.fromisoformat(f"{day}T00:00:00").replace(tzinfo=LOCAL_TZ)
    next_start = datetime.combine(start.date() + timedelta(days=1),
                                  datetime.min.time(), tzinfo=LOCAL_TZ)
    first_end = start.astimezone(timezone.utc)
    count = int((next_start.astimezone(timezone.utc) - first_end).total_seconds() // 900)
    return [MeasuredValue(first_end + QUARTER * step, step, 1.0, 15, source)
            for step in range(1, count + 1)]


def _report(sdat, esl=None, found=None, staged=None, issues=None):
    return build_report(
        found_by_type=found or {"sdat": 1, "esl": 0, "other": 0},
        staged_by_type=staged or {"sdat": 1, "esl": 0},
        issues=issues if issues is not None else [],
        sdat_data=sdat,
        esl_data=esl if esl is not None else EslDataset({}, []),
    )


def test_file_rows_and_totals_split_by_type():
    report = _report(
        SdatDataset({}, []),
        found={"sdat": 5133, "esl": 47, "other": 3},
        staged={"sdat": 5133, "esl": 47},
        issues=[{"kind": "file", "type": "esl", "reason": "Keine gültigen ESL-Zählerstände",
                 "file": "a.xml", "skippedRecords": 0},
                {"kind": "file", "type": "esl", "reason": "Keine gültigen ESL-Zählerstände",
                 "file": "b.xml", "skippedRecords": 0},
                {"kind": "record", "reason": "status E", "file": "c.xml", "skippedRecords": 4}],
    )

    assert report["files"] == [
        {"type": "sdat", "found": 5133, "processed": 5133, "skipped": 0},
        {"type": "esl", "found": 47, "processed": 45, "skipped": 2},
        {"type": "other", "found": 3, "processed": 0, "skipped": 3},
    ]
    assert report["foundFiles"] == 5183
    assert report["processedFiles"] == 5178
    assert report["skippedFiles"] == 5
    assert report["skippedRecords"] == 4


def test_other_row_is_omitted_when_every_file_had_a_type():
    report = _report(SdatDataset({}, []), found={"sdat": 2, "esl": 1, "other": 0},
                     staged={"sdat": 2, "esl": 1})
    assert [row["type"] for row in report["files"]] == ["sdat", "esl"]


def test_measurement_points_count_values_after_deduplication():
    source = _source("a.xml")
    sdat = SdatDataset({"ID742": _day_values("2024-06-03", source),
                        "ID735": _day_values("2024-06-03", source)}, [source])
    assert _report(sdat)["measurementPoints"] == 192


def test_sensor_rows_carry_direction_period_and_meter_readings():
    source = _source("a.xml")
    sdat = SdatDataset({
        "ID742": _day_values("2024-06-03", source),
        "ID26263": [MeasuredValue(datetime(2024, 7, 1, 12, tzinfo=timezone.utc), 1, 1.0, 15, source)],
    }, [source])
    reading_time = datetime(2024, 6, 3, tzinfo=timezone.utc)
    esl = EslDataset({"ID742": [EslMeterReading(reading_time, 100),
                                EslMeterReading(reading_time + timedelta(days=1), 110)]}, [])

    assert _report(sdat, esl)["sensors"] == [
        {"sensorId": "ID742", "direction": "consumption", "values": 96,
         "from": "2024-06-03", "to": "2024-06-03", "eslReadings": 2},
        {"sensorId": "ID26263", "direction": "other", "values": 1,
         "from": "2024-07-01", "to": "2024-07-01", "eslReadings": 0},
    ]


def test_sensor_period_falls_back_to_meter_reading_dates_without_sdat():
    esl = EslDataset({"ID735": [EslMeterReading(datetime(2024, 5, 4, 10, tzinfo=timezone.utc), 7)]}, [])
    assert _report(SdatDataset({}, []), esl)["sensors"] == [
        {"sensorId": "ID735", "direction": "feed-in", "values": 0,
         "from": "2024-05-04", "to": "2024-05-04", "eslReadings": 1},
    ]


def _finding(report, label):
    matches = [finding["text"] for finding in report["findings"] if finding["label"] == label]
    return matches[0] if matches else None


def test_conflicting_timestamps_are_reported_as_duplicates():
    source = _source("a.xml")
    sdat = SdatDataset({"ID742": _day_values("2024-06-03", source)}, [source], conflicts=45422)
    text = _finding(_report(sdat), "Duplikate")
    assert text is not None
    assert "45422 Zeitpunkte" in text
    assert "jüngsten Erstellungszeitpunkt" in text


def test_matching_duplicates_do_not_produce_a_finding():
    source = _source("a.xml")
    sdat = SdatDataset({"ID742": _day_values("2024-06-03", source)}, [source], conflicts=0)
    assert _finding(_report(sdat), "Duplikate") is None


def test_daylight_saving_days_are_reported_with_their_quarter_hour_counts():
    source = _source("a.xml")
    sdat = SdatDataset({"ID742": [*_day_values("2024-03-31", source),
                                  *_day_values("2024-06-03", source),
                                  *_day_values("2024-10-27", source)]}, [source])
    text = _finding(_report(sdat), "Zeitumstellung")
    assert text is not None
    assert "92 und 100 Viertelstunden" in text


def test_incomplete_days_are_not_mistaken_for_a_time_change():
    source = _source("a.xml")
    partial = _day_values("2024-06-03", source)[:10]
    sdat = SdatDataset({"ID742": partial}, [source])
    assert _finding(_report(sdat), "Zeitumstellung") is None


def test_single_value_files_without_resolution_are_reported_with_their_only_sensor():
    lonely = [_source(f"single-{index}.xml", "ID26263", resolution_unit=None)
              for index in range(32)]
    regular = _source("regular.xml", "ID742")
    sdat = SdatDataset({
        "ID742": _day_values("2024-06-03", regular),
        "ID26263": [MeasuredValue(datetime(2024, 7, 1, tzinfo=timezone.utc), 1, 1.0, 15, lonely[0])],
    }, [*lonely, regular])

    text = _finding(_report(sdat), "Verarbeitet")
    assert text is not None
    assert "32 sdat-Dateien" in text
    assert "ohne Angabe zum zeitlichen Abstand" in text
    assert "ID26263" in text
    assert "ID742" not in text


def test_files_with_resolution_unit_are_not_reported_as_single_value_files():
    source = _source("a.xml", interval_minutes=15)
    sdat = SdatDataset({"ID742": [MeasuredValue(
        datetime(2024, 7, 1, tzinfo=timezone.utc), 1, 1.0, 15, source)]}, [source])
    assert _finding(_report(sdat), "Verarbeitet") is None


def test_skipped_meters_name_the_registers_they_delivered():
    rows = (EslValueRow("8-1:1.8.0", "100", "V"),)
    esl = EslDataset({}, [EslSource("a.xml", "5442313", "2024-01-01T00:00:00", rows),
                          EslSource("b.xml", "5442313", "2024-02-01T00:00:00", rows)])
    issues = [{"kind": "meter", "meter": "5442313", "file": name, "skippedRecords": 0,
               "reason": "keine vollständigen OBIS-Paare (Hoch- und Niedertarif)"}
              for name in ("a.xml", "b.xml")]

    text = _finding(_report(SdatDataset({}, []), esl, issues=issues), "Übersprungen")
    assert text is not None
    assert "Zähler 5442313 in 2 Dateien" in text
    assert "nur Register 8-1:1.8.0" in text
    assert "kein Wirkenergie-Register für Bezug oder Einspeisung" in text


def test_skipped_meter_without_known_registers_keeps_the_original_reason():
    issues = [{"kind": "meter", "meter": "99", "file": "a.xml", "skippedRecords": 0,
               "reason": "OBIS-Gruppe 1-1:1.8 wird bereits von Meter 5442313 geliefert"}]
    text = _finding(_report(SdatDataset({}, []), issues=issues), "Übersprungen")
    assert text is not None
    assert "Zähler 99 in 1 Datei" in text
    assert "wird bereits von Meter 5442313 geliefert" in text


def test_factor_three_discrepancy_stays_a_labelled_finding():
    first = datetime(2024, 1, 1, tzinfo=timezone.utc)
    last = first + timedelta(days=1)
    series = {first: MeterReading(first, 0, 100), last: MeterReading(last, 0, 130)}
    esl = EslDataset({"ID742": [EslMeterReading(first, 100), EslMeterReading(last, 110)]}, [])
    report = build_report(found_by_type={"sdat": 0, "esl": 1, "other": 0},
                          staged_by_type={"sdat": 0, "esl": 1}, issues=[],
                          sdat_data=SdatDataset({}, []), esl_data=esl,
                          meter_readings={"ID742": series})
    assert "Faktor 3" in _finding(report, "Befund")
