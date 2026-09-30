import sys
import json
import shutil
import hashlib
import pickle
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from volt_trace.quantities import round_kwh
from volt_trace.sdat import SENSOR_DIRECTIONS, load_sdat_folder
from volt_trace.esl import load_esl_folder
from volt_trace.export import (KIND_CONSUMPTION, KIND_METER, KINDS, consumption_points,
                               meter_points, to_csv_string)

NS_SDAT = "{http://www.strom.ch}"
LOCAL_TZ = ZoneInfo("Europe/Zurich")
INTERVAL = timedelta(minutes=15)   # Länge eines sdat-Intervalls


def _detect_file_type(path: Path):
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    if root.tag.startswith(NS_SDAT):
        return "sdat"
    if root.tag == "ESLBillingData":
        return "esl"
    return None


def cmd_sort_files(src_dir: str, dataset_dir: str):
    src = Path(src_dir)
    sdat_dir = Path(dataset_dir) / "sdat"
    esl_dir = Path(dataset_dir) / "esl"
    sdat_dir.mkdir(parents=True, exist_ok=True)
    esl_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    issues = []
    for f in src.glob("*"):
        if not f.is_file():
            continue
        file_type = _detect_file_type(f)
        if file_type == "sdat":
            shutil.move(str(f), sdat_dir / f.name)
            processed += 1
        elif file_type == "esl":
            shutil.move(str(f), esl_dir / f.name)
            processed += 1
        else:
            issues.append({"file": f.name, "reason": "unbekanntes Format", "skippedRecords": 0})

    # Files lesen und Fehler sammeln (füllt gleichzeitig den Cache) - NFA-06.
    # Meter-Skips (FA-04) sind erwartet und werden hier nicht als Fehler gemeldet.
    skipped = _load(dataset_dir)[2]
    issues += [entry for entry in skipped if "meter" not in entry]

    print(json.dumps({"processedFiles": processed, "skippedFiles": len(issues), "issues": issues}))


def _load(dataset_dir: str):
    base = Path(dataset_dir).resolve()
    # Only server-generated caches are read; uploads are restricted to XML.
    cache = base / ".processed-v2.cache"
    sources = sorted([*base.glob("sdat/*.xml"), *base.glob("esl/*.xml"),
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
    sdat_data = load_sdat_folder(base / "sdat", skipped)   # dedupliziert + sortiert (FA-06)
    esl_data = load_esl_folder(base / "esl", skipped)      # ESL-Stände (HT + NT)
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
        }
        for sensor_id in sensor_ids
    ]
    print(json.dumps(result))


def _consumption_day_bucket(interval_end_utc: datetime) -> datetime.date:
    """Verbrauchstag aus Intervallende (Europe/Zurich); Mitternacht → Vortag."""
    local_end = interval_end_utc.astimezone(LOCAL_TZ)
    if (
        local_end.hour == 0
        and local_end.minute == 0
        and local_end.second == 0
        and local_end.microsecond == 0
    ):
        return local_end.date() - timedelta(days=1)
    return local_end.date()


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