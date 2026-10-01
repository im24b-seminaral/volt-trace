from datetime import datetime, timedelta, timezone

from volt_trace.compare_esl_vs_sdat import compare_esl_sdat
from volt_trace.esl import EslMeterReading
from volt_trace.sdat import MeasuredValue


def test_comparison_assigns_interval_ends_to_adjacent_esl_periods():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    values = [
        MeasuredValue(start + timedelta(minutes=15 * index), index + 1, volume)
        for index, volume in enumerate([10.0, 20.0, 30.0, 40.0, 50.0])
    ]
    readings = [
        EslMeterReading(start, 100.0),
        EslMeterReading(start + timedelta(minutes=30), 150.0),
        EslMeterReading(start + timedelta(minutes=60), 240.0),
    ]

    result = compare_esl_sdat(values, readings)

    assert [period["sdat_summe"] for period in result] == [50.0, 90.0]
    assert [period["anzahl_messwerte"] for period in result] == [2, 2]
    assert [period["verhaeltnis"] for period in result] == [1.0, 1.0]
