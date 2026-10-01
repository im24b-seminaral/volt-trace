import json
import zipfile
from pathlib import Path

from volt_trace import cli
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
    sdat, esl, _skipped = cli._load(str(destination))
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
        assert report["files"] == [
            {"type": "sdat", "found": 3, "processed": 2, "skipped": 1},
            {"type": "esl", "found": 1, "processed": 1, "skipped": 0},
            {"type": "other", "found": 3, "processed": 0, "skipped": 3},
        ]
        assert report["measurementPoints"] == 1
        assert report["sensors"] == [
            {"sensorId": "ID742", "direction": "consumption", "values": 1,
             "from": "2024-01-01", "to": "2024-01-01", "eslReadings": 1},
        ]
        assert all({"label", "text"} == set(finding) for finding in report["findings"])
        assert [finding["label"] for finding in report["findings"]] == ["Duplikate"]

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


def test_duplicate_path_is_counted_once_as_skipped(tmp_path, capsys):
    """Eine beim Sortieren verworfene Datei darf nicht zusätzlich als unlesbar zählen."""
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "same.xml").write_text(_sdat("2024-01-01T01:00:00Z", "1.0"), encoding="utf-8")
    destination = tmp_path / "out"
    taken = destination / "sdat" / "same.xml"
    taken.parent.mkdir(parents=True)
    taken.write_text(_sdat("2024-01-01T02:00:00Z", "2.5"), encoding="utf-8")

    report, sdat, _esl = _import(raw, destination, capsys)
    assert any(issue["reason"] == "Doppelter Dateipfad" for issue in report["issues"])
    assert report["files"] == [
        {"type": "sdat", "found": 1, "processed": 0, "skipped": 1},
        {"type": "esl", "found": 0, "processed": 0, "skipped": 0},
    ]
    assert (report["foundFiles"], report["processedFiles"], report["skippedFiles"]) == (1, 0, 1)
    assert [value.volume for value in sdat["ID742"]] == [2.5]


def test_conflicting_timestamp_counts_once_across_three_files(tmp_path, capsys):
    """Der Hinweis nennt Zeitpunkte, nicht Lesungen: drei Werte sind ein Widerspruch."""
    raw = tmp_path / "raw"
    raw.mkdir()
    for index, volume in enumerate(("1.0", "2.0", "3.0")):
        (raw / f"file{index}.xml").write_text(
            _sdat(f"2024-01-0{index + 1}T01:00:00Z", volume), encoding="utf-8")

    report, sdat, _esl = _import(raw, tmp_path / "out", capsys)
    assert [value.volume for value in sdat["ID742"]] == [3.0]   # jüngste Creation gewinnt
    duplicates = [f for f in report["findings"] if f["label"] == "Duplikate"]
    assert len(duplicates) == 1
    assert duplicates[0]["text"].startswith("1 Zeitpunkt mit widersprüchlichem Wert.")
