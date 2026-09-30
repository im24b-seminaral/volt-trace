import sys
import json
import csv
import shutil
import hashlib
import pickle
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

from volt_trace.sdat import load_sdat_folder
from volt_trace.esl import load_esl_folder
from volt_trace.analysis import calculate_all_meter_readings, remove_duplicates, sort_measured_values_by_time

NS_SDAT = "{http://www.strom.ch}"


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

    print(json.dumps({"processedFiles": processed, "skippedFiles": len(issues), "issues": issues}))


def _load(dataset_dir: str):
    base = Path(dataset_dir).resolve()
    # Only server-generated caches are read; uploads are restricted to XML.
    cache = base / ".processed-v1.cache"
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

    sdat_data = load_sdat_folder(base / "sdat")
    sdat_data = {sensor: remove_duplicates(sort_measured_values_by_time(values))
                 for sensor, values in sdat_data.items()}
    esl_data = load_esl_folder(base / "esl")
    meter_readings = calculate_all_meter_readings(sdat_data, esl_data)
    data = sdat_data, esl_data, meter_readings
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
    sdat_data, _esl_data, meter_readings = _load(dataset_dir)
    result = [
        {
            "sensorId": sensor_id,
            "label": sensor_id,
            "direction": "consumption" if sensor_id == "ID742" else "feed-in",
            "hasMeterReadings": sensor_id in meter_readings,
        }
        for sensor_id in sdat_data
    ]
    print(json.dumps(result))


def _aggregate_by_day(points, kind):
    by_day = {}
    for ts, value in sorted(points, key=lambda p: p[0]):
        day = ts.date()
        if kind == "consumption":
            by_day[day] = by_day.get(day, 0.0) + value
        else:
            by_day[day] = value
    return [(datetime.combine(day, datetime.min.time()), value) for day, value in sorted(by_day.items())]


def cmd_series(dataset_dir: str, sensor_id: str, kind: str, resolution: str, from_str: str, to_str: str):
    sdat_data, _esl_data, meter_readings = _load(dataset_dir)

    if kind == "consumption":
        values = sdat_data.get(sensor_id, [])
        points = [(v.timestamp, v.volume) for v in values]
    else:
        points = [(r.start_time, r.start_value) for r in meter_readings.get(sensor_id, [])]

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
    _sdat_data, _esl_data, meter_readings = _load(dataset_dir)
    readings = meter_readings.get(sensor_id, [])
    writer = csv.writer(sys.stdout)
    writer.writerow(["timestamp", "value"])
    for r in sorted(readings, key=lambda r: r.start_time):
        writer.writerow([int(r.start_time.timestamp()), r.start_value])


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
