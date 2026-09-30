import sys
import json
import csv
import shutil
import hashlib
import pickle
import tempfile
import zipfile
import stat
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from volt_trace.sdat import SENSOR_DIRECTIONS, load_sdat_folder
from volt_trace.esl import load_esl_folder
from volt_trace.analysis import calculate_all_meter_readings

NS_SDAT = "{http://www.strom.ch}"
LOCAL_TZ = ZoneInfo("Europe/Zurich")


def _detect_file_type(path: Path):
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None, "Kein gültiges XML"
    if root.tag.startswith(NS_SDAT):
        return "sdat", None
    if root.tag == "ESLBillingData":
        return "esl", None
    return None, "Unbekanntes XML-Format"


def _archive_member_parts(name: str) -> tuple[str, ...]:
    normalized = name.replace("\\", "/")
    parts = tuple(normalized.split("/"))
    if (normalized.startswith("/") or any(part in ("", ".", "..") or ":" in part for part in parts)
            or "\x00" in normalized):
        raise ValueError("Unsicherer Pfad im ZIP")
    return parts


def _extract_archive(archive_path: Path, src: Path, issues: list[dict]) -> int:
    extracted = 0
    issue_count = len(issues)
    target_root = src / "_extracted" / archive_path.relative_to(src).with_suffix("")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            if len(archive.infolist()) > 20_000:
                raise ValueError("ZIP enthält zu viele Einträge")
            total_size = 0
            for info in archive.infolist():
                if info.is_dir() or "__MACOSX" in info.filename or info.filename.endswith(".DS_Store"):
                    continue
                label = f"{archive_path.relative_to(src).as_posix()}!/{info.filename}"
                try:
                    parts = _archive_member_parts(info.filename)
                    if stat.S_ISLNK(info.external_attr >> 16):
                        raise ValueError("Symbolischer Link im ZIP")
                    total_size += info.file_size
                    if info.file_size > 256 * 1024 * 1024 or total_size > 1024 * 1024 * 1024:
                        raise ValueError("ZIP überschreitet die Grössenbegrenzung")
                    target = target_root.joinpath(*parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        raise ValueError("Doppelter Pfad im ZIP")
                    try:
                        with archive.open(info) as source, target.open("xb") as output:
                            shutil.copyfileobj(source, output, length=1024 * 1024)
                    except Exception:
                        target.unlink(missing_ok=True)
                        raise
                    extracted += 1
                except (ValueError, RuntimeError, NotImplementedError, OSError, zipfile.BadZipFile) as error:
                    issues.append({"file": label, "kind": "file", "reason": str(error), "skippedRecords": 0})
    except (ValueError, RuntimeError, NotImplementedError, OSError, zipfile.BadZipFile) as error:
        issues.append({"file": archive_path.relative_to(src).as_posix(), "kind": "file",
                       "reason": f"Ungültiges ZIP: {error}", "skippedRecords": 0})
    else:
        if extracted == 0 and len(issues) == issue_count:
            issues.append({"file": archive_path.relative_to(src).as_posix(), "kind": "file",
                           "reason": "ZIP enthält keine verwendbaren Dateien", "skippedRecords": 0})
    return extracted


def cmd_sort_files(src_dir: str, dataset_dir: str):
    src = Path(src_dir)
    destination = Path(dataset_dir)
    sdat_dir = destination / "sdat"
    esl_dir = destination / "esl"
    sdat_dir.mkdir(parents=True, exist_ok=True)
    esl_dir.mkdir(parents=True, exist_ok=True)

    issues: list[dict] = []
    archives = sorted(path for path in src.rglob("*")
                      if path.is_file() and not path.is_symlink() and path.suffix.lower() == ".zip")
    for archive_path in archives:
        _extract_archive(archive_path, src, issues)

    found = len(issues)
    staged = 0
    for file_path in sorted(path for path in src.rglob("*") if path.is_file() or path.is_symlink()):
        relative = file_path.relative_to(src)
        if ((file_path.suffix.lower() == ".zip" and not file_path.is_symlink())
                or "__MACOSX" in relative.parts
                or file_path.name.startswith("._") or file_path.name == ".DS_Store"):
            continue
        found += 1
        label = relative.as_posix()
        if file_path.is_symlink():
            issues.append({"file": label, "kind": "file", "reason": "Symbolischer Link nicht erlaubt",
                           "skippedRecords": 0})
            continue
        if file_path.suffix.lower() != ".xml":
            issues.append({"file": label, "kind": "file", "reason": "Keine XML-Datei",
                           "skippedRecords": 0})
            continue
        file_type, error = _detect_file_type(file_path)
        if file_type is None:
            issues.append({"file": label, "kind": "file", "reason": error,
                           "skippedRecords": 0})
            continue
        target = destination / file_type / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            issues.append({"file": label, "kind": "file", "reason": "Doppelter Dateipfad",
                           "skippedRecords": 0})
            continue
        shutil.move(str(file_path), target)
        staged += 1

    # Files lesen und Fehler sammeln (füllt gleichzeitig den Cache) - NFA-06.
    # Meter-Skips (FA-04) sind erwartet und werden hier nicht als Fehler gemeldet.
    sdat_data, esl_data, meter_readings, skipped = _load(dataset_dir)
    issues.extend(skipped)
    failed_staged = sum(issue.get("kind") == "file" for issue in skipped)
    imported = staged - failed_staged
    findings = _measurement_findings(meter_readings, esl_data)
    report = {"foundFiles": found, "processedFiles": imported,
              "skippedFiles": found - imported,
              "skippedRecords": sum(issue.get("skippedRecords", 0) for issue in issues),
              "issues": issues, "findings": findings}
    print(json.dumps(report))


def _measurement_findings(meter_readings, esl_data) -> list[str]:
    for sensor_id, series in meter_readings.items():
        dates = sorted(esl_data.get(sensor_id, []), key=lambda reading: reading.start_time)
        for first, last in zip(dates, dates[1:]):
            if first.start_time not in series or last.start_time not in series:
                continue
            measured_change = last.start_value - first.start_value
            calculated_change = (series[last.start_time].meter_value
                                 - series[first.start_time].meter_value)
            if measured_change and abs(calculated_change / measured_change - 3) < 0.05:
                return ["Befund: SDAT-Verbrauch und ESL-Zählerdifferenz weichen bei der "
                        "Testanlage um etwa Faktor 3 ab. Gültige Werte wurden unverändert übernommen."]
    return []


def _load(dataset_dir: str):
    base = Path(dataset_dir).resolve()
    # Only server-generated caches are read; uploads are restricted to XML.
    cache = base / ".processed-v2.cache"
    sources = sorted([*(path for folder in (base / "sdat", base / "esl")
                       for path in folder.rglob("*")
                       if path.is_file() and path.suffix.lower() == ".xml"),
                      *Path(__file__).parent.glob("*.py")])
    fingerprint = hashlib.sha256()
    for source in sources:
        stat = source.stat()
        fingerprint.update(f"{source}:{stat.st_size}:{stat.st_mtime_ns}".encode())
    key = fingerprint.hexdigest()
    try:
        with cache.open("rb") as stream:
            saved_key, data = pickle.load(stream)
        if saved_key == key:
            return data
    except (OSError, EOFError, ValueError, TypeError, AttributeError, ImportError, pickle.UnpicklingError):
        pass

    skipped = []   # defekte Files und übersprungene Datensätze (NFA-06)
    sdat_data = load_sdat_folder(base / "sdat", skipped)
    esl_data = load_esl_folder(base / "esl", skipped)
    meter_readings = calculate_all_meter_readings(sdat_data, esl_data)
    data = sdat_data, esl_data, meter_readings, skipped
    # Atomic replacement also allows simultaneous requests to finish safely.
    with tempfile.NamedTemporaryFile(dir=base, delete=False) as stream:
        temporary = Path(stream.name)
        pickle.dump((key, data), stream, protocol=pickle.HIGHEST_PROTOCOL)
    try:
        temporary.replace(cache)
    finally:
        temporary.unlink(missing_ok=True)
    return data


def cmd_sensors(dataset_dir: str):
    sdat_data, _esl_data, meter_readings, _skipped = _load(dataset_dir)
    result = [
        {
            "sensorId": sensor_id,
            "label": sensor_id,
            "direction": SENSOR_DIRECTIONS.get(sensor_id, "other"),
            "hasMeterReadings": sensor_id in meter_readings,
        }
        for sensor_id in sdat_data
    ]
    print(json.dumps(result))


def _aggregate_by_day(points, kind):
    # Tagesgrenzen auf lokaler Mitternacht (NFA-05), Ergebnis-Timestamps in UTC.
    # ts ist der Intervallbeginn (siehe sdat.py); bei Umstellung auf Intervallende (FA-05)
    # muss hier vor der Konvertierung die Resolution abgezogen werden.
    by_day = {}
    for ts, value in sorted(points, key=lambda p: p[0]):
        day = ts.astimezone(LOCAL_TZ).date()
        if kind == "consumption":
            by_day[day] = by_day.get(day, 0.0) + value
        else:
            by_day[day] = value
    return [
        (datetime.combine(day, datetime.min.time(), tzinfo=LOCAL_TZ).astimezone(timezone.utc), value)
        for day, value in sorted(by_day.items())
    ]


def cmd_series(dataset_dir: str, sensor_id: str, kind: str, resolution: str, from_str: str, to_str: str):
    sdat_data, _esl_data, meter_readings, _skipped = _load(dataset_dir)

    if kind == "consumption":
        values = sdat_data.get(sensor_id, [])
        points = [(v.timestamp, v.volume) for v in values]
    else:
        points = [(r.timestamp, r.meter_value) for r in meter_readings.get(sensor_id, {}).values()]

    if from_str:
        from_dt = datetime.fromisoformat(from_str.replace("Z", "+00:00"))
        points = [(t, v) for t, v in points if t >= from_dt]
    if to_str:
        to_dt = datetime.fromisoformat(to_str.replace("Z", "+00:00"))
        points = [(t, v) for t, v in points if t <= to_dt]

    points = _aggregate_by_day(points, kind) if resolution == "day" else sorted(points, key=lambda p: p[0])

    print(json.dumps([{
        "sensorId": sensor_id,
        "data": [{"ts": ts.isoformat(), "value": value} for ts, value in points],
    }]))


def cmd_export(dataset_dir: str, sensor_id: str):
    _sdat_data, _esl_data, meter_readings, _skipped = _load(dataset_dir)
    series = meter_readings.get(sensor_id, {})
    writer = csv.writer(sys.stdout)
    writer.writerow(["timestamp", "value"])
    for r in series.values():   # bereits sortiert (check_series)
        writer.writerow([int(r.timestamp.timestamp()), r.meter_value])


if __name__ == "__main__":
    command = sys.argv[1]
    args = sys.argv[2:]
    if command == "sort-files":
        cmd_sort_files(*args)
    elif command == "sensors":
        cmd_sensors(*args)
    elif command == "series":
        while len(args) < 6:
            args.append("")
        cmd_series(*args)
    elif command == "export":
        cmd_export(*args)
    else:
        print(f"unbekanntes Kommando: {command}", file=sys.stderr)
        sys.exit(1)
