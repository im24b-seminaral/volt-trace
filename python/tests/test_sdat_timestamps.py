"""FA-05: SDAT-Zeitstempel = Intervallende, Validierung Auflösung und Sequenz."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from volt_trace.sdat import load_sdat_folder, parse_sdat_file

NS = "http://www.strom.ch"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_sdat_xml(
    *,
    start: datetime,
    end: datetime,
    count: int,
    resolution: int = 15,
    unit: str = "MIN",
    document_suffix: str = "ID742",
    volumes: list[float] | None = None,
    unit_in_xml: bool = True,
    skip_sequence: int | None = None,
) -> str:
    if volumes is None:
        volumes = [0.1] * count
    observations = []
    for seq in range(1, count + 1):
        if skip_sequence == seq:
            continue
        vol = volumes[seq - 1]
        observations.append(
            f'<rsm:Observation><rsm:Position><rsm:Sequence>{seq}</rsm:Sequence></rsm:Position>'
            f'<rsm:Volume>{vol}</rsm:Volume></rsm:Observation>'
        )
    unit_block = (
        f"<rsm:Unit>{unit}</rsm:Unit>" if unit_in_xml else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:InstanceDocument xmlns:rsm="{NS}">
  <rsm:Creation>{_iso(start)}</rsm:Creation>
  <rsm:DocumentID>meter_{document_suffix}</rsm:DocumentID>
  <rsm:Interval>
    <rsm:StartDateTime>{_iso(start)}</rsm:StartDateTime>
    <rsm:EndDateTime>{_iso(end)}</rsm:EndDateTime>
  </rsm:Interval>
  <rsm:Resolution>
    <rsm:Resolution>{resolution}</rsm:Resolution>
    {unit_block}
  </rsm:Resolution>
  {''.join(observations)}
</rsm:InstanceDocument>"""


def _write_xml(tmp_path: Path, name: str, xml: str) -> Path:
    path = tmp_path / name
    path.write_text(xml, encoding="utf-8")
    return path


def test_normal_day_96_interval_ends(tmp_path):
    start = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 15, 23, 0, tzinfo=timezone.utc)
    _write_xml(tmp_path, "day.xml", build_sdat_xml(start=start, end=end, count=96))
    _, data = parse_sdat_file(tmp_path / "day.xml")
    values = data["ID742"]
    assert len(values) == 96
    assert max(v.sequence for v in values) == 96
    assert values[0].timestamp == start + timedelta(minutes=15)
    assert values[-1].timestamp == end
    assert values[0].resolution_minutes == 15


def test_dst_spring_92_values(tmp_path):
    start = datetime(2024, 3, 30, 23, 0, tzinfo=timezone.utc)
    end = datetime(2024, 3, 31, 22, 0, tzinfo=timezone.utc)
    _write_xml(tmp_path, "spring.xml", build_sdat_xml(start=start, end=end, count=92))
    _, data = parse_sdat_file(tmp_path / "spring.xml")
    assert len(data["ID742"]) == 92


def test_dst_autumn_100_values(tmp_path):
    start = datetime(2024, 10, 26, 22, 0, tzinfo=timezone.utc)
    end = datetime(2024, 10, 27, 23, 0, tzinfo=timezone.utc)
    _write_xml(tmp_path, "autumn.xml", build_sdat_xml(start=start, end=end, count=100))
    _, data = parse_sdat_file(tmp_path / "autumn.xml")
    assert len(data["ID742"]) == 100


def test_month_2976_values(tmp_path):
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 2, 1, 0, 0, tzinfo=timezone.utc)
    _write_xml(tmp_path, "month.xml", build_sdat_xml(start=start, end=end, count=2976))
    _, data = parse_sdat_file(tmp_path / "month.xml")
    assert len(data["ID742"]) == 2976


def test_invalid_unit_skipped(tmp_path):
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
    _write_xml(
        tmp_path,
        "bad_unit.xml",
        build_sdat_xml(start=start, end=end, count=96, unit="SEC"),
    )
    good = build_sdat_xml(
        start=datetime(2024, 2, 1, 0, 0, tzinfo=timezone.utc),
        end=datetime(2024, 2, 2, 0, 0, tzinfo=timezone.utc),
        count=96,
    )
    _write_xml(tmp_path, "good.xml", good)
    skipped = []
    data = load_sdat_folder(tmp_path, skipped)
    assert "ID742" in data
    assert len(data["ID742"]) == 96
    assert any("MIN" in s["reason"] or "Einheit" in s["reason"] for s in skipped)


def test_incomplete_sequence_skipped(tmp_path):
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
    _write_xml(
        tmp_path,
        "gap.xml",
        build_sdat_xml(start=start, end=end, count=96, skip_sequence=50),
    )
    skipped = []
    data = load_sdat_folder(tmp_path, skipped)
    assert data == {}
    assert skipped and "Sequenz" in skipped[0]["reason"]
