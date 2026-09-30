import json
from datetime import datetime, timezone
from unittest.mock import Mock

from volt_trace import cli
from volt_trace.sdat import MeasuredValue


def test_cached_dataset_serves_different_views_and_rebuilds(tmp_path, monkeypatch, capsys):
    (tmp_path / "sdat").mkdir()
    (tmp_path / "esl").mkdir()
    source = tmp_path / "sdat" / "sample.xml"
    source.write_text("<sample/>")
    stamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
    loader = Mock(return_value={"ID735": [MeasuredValue(stamp, 1, 2.5)]})
    calculate = Mock(return_value={})
    monkeypatch.setattr(cli, "load_sdat_folder", loader)
    monkeypatch.setattr(cli, "load_esl_folder", Mock(return_value={}))
    monkeypatch.setattr(cli, "calculate_all_meter_readings", calculate)

    cli.cmd_sensors(str(tmp_path))
    assert json.loads(capsys.readouterr().out)[0]["sensorId"] == "ID735"
    cli.cmd_series(str(tmp_path), "ID735", "consumption", "day", "", "")
    assert json.loads(capsys.readouterr().out)[0]["data"][0]["value"] == 2.5
    cli.cmd_series(str(tmp_path), "ID735", "consumption", "15min", "2021-01-01T00:00:00Z", "")
    assert json.loads(capsys.readouterr().out)[0]["data"] == []
    assert loader.call_count == calculate.call_count == 1

    source.write_text("<sample changed='true'/>")
    cli._load(str(tmp_path))
    assert loader.call_count == 2

    (tmp_path / ".processed-v1.cache").write_bytes(b"broken cache")
    cli._load(str(tmp_path))
    assert loader.call_count == 3
