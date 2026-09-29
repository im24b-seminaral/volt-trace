import shutil
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uuid
import io
import csv

from volt_trace.sdat import load_sdat_folder, MeasuredValue
from volt_trace.esl import load_esl_folder
from volt_trace.analysis import calculate_all_meter_readings

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# einfachster Speicher für den Schulkontext: alles im RAM, key = datasetId
datasets: dict[str, dict] = {}


def _detect_file_type(path: Path) -> Literal["sdat", "esl", None]:
    """Schaut sich nur den Root-Tag an, ohne die ganze Datei zu verarbeiten."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return None
    if root.tag.startswith("{http://www.strom.ch}"):
        return "sdat"
    if root.tag == "ESLBillingData":
        return "esl"
    return None


@app.post("/datasets")
async def upload(files: list[UploadFile]):
    dataset_id = str(uuid.uuid4())
    work_dir = Path(tempfile.mkdtemp(prefix=f"volt_trace_{dataset_id}_"))
    sdat_dir = work_dir / "sdat"
    esl_dir = work_dir / "esl"
    sdat_dir.mkdir()
    esl_dir.mkdir()

    issues = []
    skipped = 0

    for file in files:
        raw_path = work_dir / file.filename
        with open(raw_path, "wb") as f:
            f.write(await file.read())

        file_type = _detect_file_type(raw_path)
        if file_type == "sdat":
            shutil.move(raw_path, sdat_dir / file.filename)
        elif file_type == "esl":
            shutil.move(raw_path, esl_dir / file.filename)
        else:
            skipped += 1
            issues.append({"file": file.filename, "reason": "unbekanntes Format", "skippedRecords": 0})

    sdat_data = load_sdat_folder(sdat_dir)
    esl_data = load_esl_folder(esl_dir)
    meter_readings = calculate_all_meter_readings(sdat_data, esl_data)

    datasets[dataset_id] = {
        "sdat": sdat_data,
        "esl": esl_data,
        "meter_readings": meter_readings,
    }
    shutil.rmtree(work_dir)  # Rohdaten liegen jetzt im RAM, tmp-Ordner nicht mehr nötig

    return {
        "datasetId": dataset_id,
        "processedFiles": len(files) - skipped,
        "skippedFiles": skipped,
        "issues": issues,
    }


@app.get("/datasets/{dataset_id}/sensors")
def sensors(dataset_id: str):
    data = datasets[dataset_id]
    result = []
    for sensor_id, values in data["sdat"].items():
        result.append({
            "sensorId": sensor_id,
            "label": sensor_id,
            "direction": "consumption" if sensor_id == "ID742" else "feed-in",
            "hasMeterReadings": sensor_id in data["meter_readings"],
        })
    return result


@app.get("/datasets/{dataset_id}/series")
def series(dataset_id: str, sensorId: str, kind: str, resolution: str, from_: str = None, to: str = None):
    data = datasets[dataset_id]

    if kind == "consumption":
        points = [(mv.timestamp, mv.volume) for mv in data["sdat"].get(sensorId, [])]
    else:  # "meter-reading"
        points = [(r.start_time, r.start_value) for r in data["meter_readings"].get(sensorId, [])]

    if resolution == "day":
        points = _aggregate_by_day(points, kind)

    return [{
        "sensorId": sensorId,
        "data": [{"ts": ts.isoformat(), "value": value} for ts, value in points],
    }]


def _aggregate_by_day(points, kind):
    """kind=consumption -> pro Tag summieren; kind=meter-reading -> letzter Wert des Tages."""
    by_day: dict = {}
    for ts, value in sorted(points):
        day = ts.date()
        if kind == "consumption":
            by_day[day] = by_day.get(day, 0) + value
        else:
            by_day[day] = value  # überschreibt mit dem jeweils letzten Wert des Tages
    return [(datetime.combine(day, datetime.min.time()), value) for day, value in by_day.items()]


@app.get("/datasets/{dataset_id}/sensors/{sensor_id}/export.csv")
def export_csv_endpoint(dataset_id: str, sensor_id: str):
    readings = datasets[dataset_id]["meter_readings"].get(sensor_id, [])

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["timestamp", "value"])
    for r in sorted(readings, key=lambda r: r.start_time):
        writer.writerow([int(r.start_time.timestamp()), r.start_value])

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={sensor_id}.csv"},
    )