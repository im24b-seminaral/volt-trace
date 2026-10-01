"""
Sichert den Vertrag, auf den sich die Upload-Karte stützt: stdout trägt nur den
Report, der Fortschritt geht als @progress-Zeilen auf stderr - und nur dann,
wenn VOLT_TRACE_PROGRESS gesetzt ist.
"""

import json
import shutil
from pathlib import Path

from volt_trace import cli

FIXTURES = Path(__file__).parent / "fixtures"


def _stage(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "raw"
    source.mkdir()
    copied = 0
    for xml_file in sorted(FIXTURES.rglob("*.xml")):
        shutil.copy(xml_file, source / f"{copied}_{xml_file.name}")
        copied += 1
    assert copied, "Fixtures fehlen"
    return source, tmp_path / "dataset"


def _events(stderr: str) -> list[dict]:
    return [json.loads(line[len("@progress "):])
            for line in stderr.splitlines() if line.startswith("@progress ")]


def test_progress_is_silent_without_the_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("VOLT_TRACE_PROGRESS", raising=False)
    source, destination = _stage(tmp_path)

    cli.cmd_sort_files(str(source), str(destination))

    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["foundFiles"] > 0


def test_progress_events_reach_stderr_and_leave_stdout_clean(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VOLT_TRACE_PROGRESS", "1")
    source, destination = _stage(tmp_path)

    cli.cmd_sort_files(str(source), str(destination))

    captured = capsys.readouterr()
    report = json.loads(captured.out)   # stdout bleibt reines JSON
    events = _events(captured.err)
    steps = [event["step"] for event in events]

    # Lese-Schritte melden sich nur, wenn es solche Dateien gibt; Rahmen steht fest.
    assert steps[0] == "sort" and steps[-1] == "prepare"
    for event in events:
        if "total" in event:
            assert 0 <= event["done"] <= event["total"]
    sort_totals = {event["total"] for event in events if event["step"] == "sort"}
    assert sort_totals == {report["foundFiles"]}


def test_cached_run_still_reports_the_reading_steps(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VOLT_TRACE_PROGRESS", "1")
    source, destination = _stage(tmp_path)
    cli.cmd_sort_files(str(source), str(destination))
    capsys.readouterr()

    cli._load(str(destination), cli.Progress())   # zweiter Lauf trifft den Cache

    steps = [event["step"] for event in _events(capsys.readouterr().err)]
    assert steps == ["sdat", "esl"]
