from datetime import datetime, timezone
from pathlib import Path

from volt_trace.esl import (
    _effektiver_zaehlerstand_pro_gruppe,
    _obis_gruppe,
    parse_esl_file,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_obis_gruppe_entfernt_tarifregister():
    assert _obis_gruppe("1-1:1.8.1") == "1-1:1.8"
    assert _obis_gruppe("1-1:2.8.2") == "1-1:2.8"
    assert _obis_gruppe("1-1:1.8.0") is None


def test_effektiver_zaehlerstand_summiert_hoch_und_niedertarif():
    werte = {
        "1-1:1.8.1": 100.5,
        "1-1:1.8.2": 200.25,
        "1-1:2.8.1": 10.1,
        "1-1:2.8.2": 5.9,
    }
    summen = _effektiver_zaehlerstand_pro_gruppe(werte)
    assert summen["1-1:1.8"] == 300.75
    assert summen["1-1:2.8"] == 16.0


def test_effektiver_zaehlerstand_ohne_beide_register():
    werte = {"1-1:1.8.1": 100.5, "1-1:2.8.1": 10.1, "1-1:2.8.2": 5.9}
    summen = _effektiver_zaehlerstand_pro_gruppe(werte)
    assert "1-1:1.8" not in summen
    assert summen["1-1:2.8"] == 16.0


def test_parse_esl_file_summiert_id742_und_id735():
    result = parse_esl_file(FIXTURES / "sample.esl.xml")
    assert len(result["ID742"]) == 1
    assert result["ID742"][0].start_value == 300.75
    assert result["ID735"][0].start_value == 16.0


def test_parse_esl_file_konvertiert_end_nach_utc_winterzeit():
    result = parse_esl_file(FIXTURES / "sample.esl.xml")
    ts = result["ID742"][0].start_time
    assert ts == datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)


def test_parse_esl_file_fehlendes_tarifregister_laesst_sensor_aus():
    result = parse_esl_file(FIXTURES / "sample_incomplete_tariff.esl.xml")
    assert "ID742" not in result
    assert result["ID735"][0].start_value == 16.0
