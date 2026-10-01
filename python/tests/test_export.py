"""Tests für den Export-Befehl der CLI: CSV (FA-10) und JSON (FA-13)."""
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from volt_trace import cli

START = datetime(2024, 1, 14, 23, tzinfo=timezone.utc)


@pytest.fixture
def daten(monkeypatch):
    sdat = {"ID742": [SimpleNamespace(timestamp=START, volume=0.25)]}
    esl = {"ID742": [SimpleNamespace(start_time=START, start_value=1000.0)]}
    monkeypatch.setattr(cli, "_load", lambda _: (sdat, esl, []))


def _export(capsysbinary, *args):
    cli.cmd_export("unused", "ID742", *args)
    return capsysbinary.readouterr().out.decode("utf-8")


def test_csv_bleibt_standard(daten, capsysbinary):
    assert _export(capsysbinary, "verbrauch") == f"timestamp,value\n{int(START.timestamp())},0.2500\n"


@pytest.mark.parametrize("kind,value", [("verbrauch", 0.25), ("zaehlerstand", 1000.0)])
def test_json_export(daten, capsysbinary, kind, value):
    assert json.loads(_export(capsysbinary, kind, "json")) == [
        {"sensorId": "ID742", "data": [{"ts": str(int(START.timestamp())), "value": value}]}]


def test_unbekanntes_format(daten):
    with pytest.raises(SystemExit) as exit_info:
        cli.cmd_export("unused", "ID742", "verbrauch", "xml")
    assert exit_info.value.code == 2
