import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from volt_trace import cli
from volt_trace.analysis import MeterReading
from volt_trace.esl import EslMeterReading
from volt_trace.sdat import load_sdat_folder


def _sdat(creation: str, volume: str, complete: bool = True) -> str:
    interval = (
        "<rsm:Interval><rsm:StartDateTime>2024-01-01T00:00:00Z</rsm:StartDateTime>"
        "<rsm:EndDateTime>2024-01-01T00:15:00Z</rsm:EndDateTime></rsm:Interval>"
        if complete else ""
    )
    return (
        '<rsm:Root xmlns:rsm="http://www.strom.ch">'
        f"<rsm:InstanceDocument><rsm:DocumentID>meter_ID742</rsm:DocumentID>"
        f"<rsm:Creation>{creation}</rsm:Creation><rsm:Status>V</rsm:Status>"
        f"</rsm:InstanceDocument>{interval}"
        "<rsm:Resolution><rsm:Resolution>15</rsm:Resolution><rsm:Unit>MIN</rsm:Unit></rsm:Resolution>"
        f"<rsm:Observation><rsm:Position><rsm:Sequence>1</rsm:Sequence></rsm:Position>"
        f"<rsm:Volume>{volume}</rsm:Volume></rsm:Observation></rsm:Root>"
    )


ESL = (
    '<ESLBillingData><Meter factoryNo="38157930"><TimePeriod end="2024-01-01T00:00:00">'
    '<ValueRow obis="1-1:1.8.1" value="100" status="V"/>'
    '<ValueRow obis="1-1:1.8.2" value="200" status="V"/>'
    '<ValueRow obis="1-1:2.8.1" value="50" status="E"/>'
    '</TimePeriod></Meter></ESLBillingData>'
)


def _files() -> dict[str, str]:
    return {
        "nested/a/shared.xml": _sdat("2024-01-01T01:00:00Z", "1.0"),
        "nested/b/shared.xml": _sdat("2024-01-01T02:00:00Z", "2.5"),
        "nested/esl/reference.xml": ESL,
        "nested/broken.xml": "<broken>",
        "nested/empty.xml": "",
        "nested/incomplete.xml": _sdat("2024-01-01T03:00:00Z", "3.0", complete=False),
        "nested/notes.txt": "not XML",
    }


def _import(raw: Path, destination: Path, capsys):
    cli.cmd_sort_files(str(raw), str(destination))
    report = json.loads(capsys.readouterr().out)
    sdat, esl, _series, _skipped = cli._load(str(destination))
    return report, sdat, esl


def test_folder_and_zip_import_keep_nested_files_and_metadata(tmp_path, capsys):
    files = _files()
    folder_raw = tmp_path / "folder_raw"
    for name, contents in files.items():
        target = folder_raw / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")

    zip_raw = tmp_path / "zip_raw"
    zip_raw.mkdir()
    with zipfile.ZipFile(zip_raw / "dataset.zip", "w") as archive:
        for name, contents in files.items():
            archive.writestr(name, contents)

    folder_report, folder_sdat, folder_esl = _import(folder_raw, tmp_path / "folder_out", capsys)
    zip_report, zip_sdat, zip_esl = _import(zip_raw, tmp_path / "zip_out", capsys)

    for report in (folder_report, zip_report):
        assert (report["foundFiles"], report["processedFiles"], report["skippedFiles"]) == (7, 3, 4)
        assert report["skippedRecords"] == 1
        assert {issue["kind"] for issue in report["issues"]} == {"file", "record"}
        assert any(issue["status"] == "E" and issue["obis"] == "1-1:2.8.1"
                   for issue in report["issues"] if issue["kind"] == "record")

    assert [value.volume for value in folder_sdat["ID742"]] == [2.5]
    assert [value.volume for value in zip_sdat["ID742"]] == [2.5]
    assert len(folder_sdat.sources) == len(zip_sdat.sources) == 2
    assert [source.creation.isoformat() for source in folder_sdat.sources] == [
        "2024-01-01T01:00:00+00:00", "2024-01-01T02:00:00+00:00"]
    assert folder_esl["ID742"][0].start_value == zip_esl["ID742"][0].start_value == 300
    assert len(folder_esl.sources) == len(zip_esl.sources) == 1

    sdat_source = folder_sdat["ID742"][0].source
    assert sdat_source is not None
    assert sdat_source.file.endswith("nested/b/shared.xml")
    assert sdat_source.document_id == "meter_ID742"
    assert sdat_source.creation.isoformat() == "2024-01-01T02:00:00+00:00"
    assert sdat_source.interval_start.isoformat() == "2024-01-01T00:00:00+00:00"
    assert sdat_source.interval_end.isoformat() == "2024-01-01T00:15:00+00:00"
    assert sdat_source.resolution_minutes == 15
    assert sdat_source.resolution_unit == "MIN"
    assert sdat_source.document_status == "V"

    esl_source = folder_esl["ID742"][0].source
    assert esl_source is not None
    assert esl_source.factory_no == "38157930"
    assert esl_source.time_period_end == "2024-01-01T00:00:00"
    assert [(row.obis, row.value, row.status) for row in esl_source.rows] == [
        ("1-1:1.8.1", "100", "V"),
        ("1-1:1.8.2", "200", "V"),
        ("1-1:2.8.1", "50", "E"),
    ]


def test_invalid_zip_and_unsafe_member_are_reported_without_extracting_outside(tmp_path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "invalid.zip").write_bytes(b"not a ZIP")
    with zipfile.ZipFile(raw / "unsafe.zip", "w") as archive:
        archive.writestr("../escape.xml", _sdat("2024-01-01T01:00:00Z", "1"))

    report, sdat, esl = _import(raw, tmp_path / "out", capsys)
    assert (report["foundFiles"], report["processedFiles"], report["skippedFiles"]) == (2, 0, 2)
    assert report["processedFiles"] == 0
    assert any("Ungültiges ZIP" in issue["reason"] for issue in report["issues"])
    assert any("Unsicherer Pfad" in issue["reason"] for issue in report["issues"])
    assert not (tmp_path / "escape.xml").exists()
    assert sdat == esl == {}


def test_equal_creation_uses_relative_path_to_break_tie(tmp_path):
    for folder, volume in (("a", "1.0"), ("z", "2.0")):
        target = tmp_path / folder / "shared.xml"
        target.parent.mkdir()
        target.write_text(_sdat("2024-01-01T01:00:00Z", volume), encoding="utf-8")
    readings = load_sdat_folder(tmp_path)
    assert readings["ID742"][0].volume == 2.0
    assert readings["ID742"][0].source.file == "z/shared.xml"
    assert len(readings.sources) == 2


def test_factor_three_discrepancy_is_a_finding_not_a_parse_error():
    first = datetime(2024, 1, 1, tzinfo=timezone.utc)
    last = first + timedelta(days=1)
    series = {first: MeterReading(first, 0, 100), last: MeterReading(last, 0, 130)}
    esl = {"ID742": [EslMeterReading(first, 100), EslMeterReading(last, 110)]}
    findings = cli._measurement_findings({"ID742": series}, esl)
    assert len(findings) == 1
    assert "Faktor 3" in findings[0]
