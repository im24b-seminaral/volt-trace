import hashlib
import json
import pickle
import shutil
import stat
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from volt_trace.analysis import calculate_all_meter_readings
from volt_trace.esl import load_esl_folder
from volt_trace.export import (
    KIND_CONSUMPTION,
    KIND_METER,
    KINDS,
    consumption_points,
    meter_points,
    to_csv_string,
)
from volt_trace.localtime import LOCAL_TZ
from volt_trace.localtime import consumption_day_bucket as _consumption_day_bucket
from volt_trace.progress import Progress
from volt_trace.quantities import round_kwh
from volt_trace.report import build_report
from volt_trace.sdat import SENSOR_DIRECTIONS, load_sdat_folder

NS_SDAT = "{http://www.strom.ch}"
INTERVAL = timedelta(minutes=15)   # Länge eines sdat-Intervalls


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
    progress = Progress()
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

    found_by_type = {"sdat": 0, "esl": 0, "other": len(issues)}
    staged_by_type = {"sdat": 0, "esl": 0}
    candidates = sorted(path for path in src.rglob("*") if path.is_file() or path.is_symlink())
    progress.send("sort", 0, len(candidates))
    for sorted_count, file_path in enumerate(candidates, start=1):
        progress.send("sort", sorted_count, len(candidates))
        relative = file_path.relative_to(src)
        if ((file_path.suffix.lower() == ".zip" and not file_path.is_symlink())
                or "__MACOSX" in relative.parts
                or file_path.name.startswith("._") or file_path.name == ".DS_Store"):
            continue
        label = relative.as_posix()
        if file_path.is_symlink():
            found_by_type["other"] += 1
            issues.append({"file": label, "kind": "file", "reason": "Symbolischer Link nicht erlaubt",
                           "skippedRecords": 0})
            continue
        if file_path.suffix.lower() != ".xml":
            found_by_type["other"] += 1
            issues.append({"file": label, "kind": "file", "reason": "Keine XML-Datei",
                           "skippedRecords": 0})
            continue
        file_type, error = _detect_file_type(file_path)
        if file_type is None:
            found_by_type["other"] += 1
            issues.append({"file": label, "kind": "file", "reason": error,
                           "skippedRecords": 0})
            continue
        found_by_type[file_type] += 1
        target = destination / file_type / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            issues.append({"file": label, "kind": "file",
                           "reason": "Doppelter Dateipfad", "skippedRecords": 0})
            continue
        shutil.move(str(file_path), target)
        staged_by_type[file_type] += 1

    # Files lesen und Fehler sammeln (füllt gleichzeitig den Cache) - NFA-06.
    # Meter-Skips (FA-04) sind erwartet und werden hier nicht als Fehler gemeldet.
    sdat_data, esl_data, skipped = _load(dataset_dir, progress)
    issues.extend(skipped)
    progress.send("prepare")
    report = build_report(
        found_by_type=found_by_type, staged_by_type=staged_by_type, issues=issues,
        sdat_data=sdat_data, esl_data=esl_data,
        meter_readings=calculate_all_meter_readings(sdat_data, esl_data),
    )
    print(json.dumps(report))


def _count_xml(folder: Path) -> int:
    return sum(1 for path in folder.rglob("*") if path.is_file() and path.suffix.lower() == ".xml")


def _load(dataset_dir: str, progress: Progress | None = None):
    progress = progress or Progress(enabled=False)
    base = Path(dataset_dir).resolve()
    # Only server-generated caches are read; uploaded archives are extracted before parsing.
    cache = base / ".processed-v3.cache"
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
            # Die Lese-Schritte laufen nicht; die Karte braucht trotzdem einen
            # Endstand, sonst bleiben sie bis zum Schluss als offen stehen.
            for step, folder in (("sdat", base / "sdat"), ("esl", base / "esl")):
                total = _count_xml(folder)
                progress.send(step, total, total)
            return data
    except (OSError, EOFError, ValueError, TypeError, AttributeError, ImportError, pickle.UnpicklingError):
        pass

    # Die Skips tragen ihren Dateityp, damit der Bericht je Typ zählen kann.
    sdat_skipped: list[dict] = []   # defekte Files und übersprungene Datensätze (NFA-06)
    esl_skipped: list[dict] = []
    sdat_data = load_sdat_folder(base / "sdat", sdat_skipped,   # dedupliziert + sortiert (FA-06)
                                 lambda done, total: progress.send("sdat", done, total))
    esl_data = load_esl_folder(base / "esl", esl_skipped,       # ESL-Stände (HT + NT)
                               lambda done, total: progress.send("esl", done, total))
    skipped = [*({**entry, "type": "sdat"} for entry in sdat_skipped),
               *({**entry, "type": "esl"} for entry in esl_skipped)]
    data = sdat_data, esl_data, skipped
    # Atomic replacement also allows simultaneous requests to finish safely.
    with tempfile.NamedTemporaryFile(dir=base, delete=False) as stream:
        temporary = Path(stream.name)
        pickle.dump((key, data), stream, protocol=pickle.HIGHEST_PROTOCOL)
    try:
        temporary.replace(cache)
    finally:
        temporary.unlink(missing_ok=True)
    return data


def _date_range(days):
    dates = list(days)
    return [str(min(dates)), str(max(dates))] if dates else []


def cmd_sensors(dataset_dir: str):
    sdat_data, esl_data, _skipped = _load(dataset_dir)
    sensor_ids = sorted(set(sdat_data) | set(esl_data))
    result = [
        {
            "sensorId": sensor_id,
            "label": sensor_id,
            "direction": SENSOR_DIRECTIONS.get(sensor_id, "other"),
            "hasConsumption": sensor_id in sdat_data,
            "hasMeterReadings": sensor_id in esl_data,
            "consumptionDates": _date_range(_consumption_day_bucket(v.timestamp) for v in sdat_data.get(sensor_id, [])),
            "meterReadingDates": _date_range(r.start_time.astimezone(LOCAL_TZ).date() for r in esl_data.get(sensor_id, [])),
        }
        for sensor_id in sensor_ids
    ]
    print(json.dumps(result))


def _aggregate_by_day(points, kind):
    # Tagesgrenzen auf lokaler Mitternacht (NFA-05), Ergebnis-Timestamps in UTC.
    # Verbrauch: ts = Intervallende (FA-05).
    by_day = {}
    for point in sorted(points, key=lambda p: p[0]):
        ts, value = point[0], point[1]
        if kind == "consumption":
            day = _consumption_day_bucket(ts)
            by_day[day] = by_day.get(day, 0.0) + value
        else:
            day = ts.astimezone(LOCAL_TZ).date()
            by_day[day] = value
    if kind == "consumption":
        by_day = {day: round_kwh(total) for day, total in by_day.items()}
    return [
        (datetime.combine(day, datetime.min.time(), tzinfo=LOCAL_TZ).astimezone(timezone.utc),
         round(value, 4))
        for day, value in sorted(by_day.items())
    ]


def cmd_series(dataset_dir: str, sensor_id: str, kind: str, resolution: str, from_str: str, to_str: str):
    sdat_data, esl_data, _skipped = _load(dataset_dir)

    if kind == "consumption":
        points = [(v.timestamp, v.volume) for v in sdat_data.get(sensor_id, [])]
    else:
        points = [(r.start_time, r.start_value) for r in esl_data.get(sensor_id, [])]

    if from_str:
        from_dt = datetime.fromisoformat(from_str.replace("Z", "+00:00"))
        if kind == "consumption":
            points = [(t, v) for t, v in points if t > from_dt]
        else:
            points = [(t, v) for t, v in points if t >= from_dt]
    if to_str:
        to_dt = datetime.fromisoformat(to_str.replace("Z", "+00:00"))
        points = [(t, v) for t, v in points if t <= to_dt]

    if kind == "consumption" and resolution == "day":
        points = _aggregate_by_day(points, kind)
    else:
        points = sorted(points, key=lambda p: p[0])   # ESL nie aggregieren

    print(json.dumps([{
        "sensorId": sensor_id,
        "data": [{"ts": ts.isoformat(), "value": value} for ts, value in points],
    }]))


def cmd_export(dataset_dir: str, sensor_id: str, kind: str):
    if kind not in KINDS:
        print(f"Unbekannte Exportart: {kind}", file=sys.stderr)
        sys.exit(2)
    sdat_data, esl_data, _skipped = _load(dataset_dir)
    points = (consumption_points(sdat_data) if kind == KIND_CONSUMPTION
              else meter_points(esl_data)).get(sensor_id)
    if not points:
        print(f"Für {sensor_id} liegen keine Daten für den Export '{kind}' vor.", file=sys.stderr)
        sys.exit(1)
    sys.stdout.buffer.write(to_csv_string(points).encode("utf-8"))


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
