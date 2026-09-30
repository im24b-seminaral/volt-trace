import csv
import io
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

DECIMALS = 4
SENSOR_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass
class DataPoint:
    """Ein Zählerstand zu einem Zeitpunkt."""
    time: datetime
    value: float

    def __post_init__(self) -> None:
        if self.time.tzinfo is None:
            raise ValueError(f"Zeitstempel ohne Zeitzone, erwartet UTC: {self.time}")

    def to_unix(self) -> int:
        return int(self.time.timestamp())


@dataclass
class JsonEntry:
    ts: str
    value: float


@dataclass
class SensorExport:
    sensorId: str
    data: List[JsonEntry] = field(default_factory=list)

    @classmethod
    def from_points(cls, sensor_id: str, points: List[DataPoint]) -> "SensorExport":
        entries = [JsonEntry(str(p.to_unix()), round(p.value, DECIMALS))
                   for p in _sort_points(points)]
        return cls(sensor_id, entries)


def _check_sensor_id(sensor_id: str) -> str:
    if not SENSOR_ID_PATTERN.match(sensor_id):
        raise ValueError(f"Ungültige Sensorkennung: {sensor_id!r}")
    return sensor_id


def _sort_points(points: List[DataPoint]) -> List[DataPoint]:
    return sorted(points, key=lambda p: p.time)


def to_csv_string(points: List[DataPoint]) -> str:
    """Gibt die Zählerstände eines Sensors als CSV-Text zurück (timestamp,value)."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["timestamp", "value"])
    for p in _sort_points(points):
        writer.writerow([p.to_unix(), f"{p.value:.{DECIMALS}f}"])
    return buffer.getvalue()


def to_json_payload(data: Dict[str, List[DataPoint]]) -> list:
    """Baut das Format [{sensorId, data: [{ts, value}]}] für JSON-Datei und HTTP POST."""
    return [asdict(SensorExport.from_points(_check_sensor_id(sid), pts))
            for sid, pts in sorted(data.items())]


def to_json_string(data: Dict[str, List[DataPoint]]) -> str:
    return json.dumps(to_json_payload(data), indent=2)


def export_csv(data: Dict[str, List[DataPoint]], target_folder: Path) -> List[Path]:
    """Schreibt eine CSV-Datei pro Sensor und gibt die Pfade der erstellten Dateien zurück."""
    target_folder = Path(target_folder)
    target_folder.mkdir(parents=True, exist_ok=True)
    created_files = []

    for sensor_id, points in data.items():
        file = target_folder / f"{_check_sensor_id(sensor_id)}.csv"
        with open(file, "w", newline="", encoding="utf-8") as f:
            f.write(to_csv_string(points))
        created_files.append(file)

    return created_files


def export_esl_comparison_csv(comparisons: list, target_file: Path) -> Path:
    """Schreibt den Soll-Ist-Vergleich an den ESL-Stichtagen (Liste von EslComparison)."""
    target_file = Path(target_file)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["stichtag", "sensor", "esl", "berechnet", "delta", "status"])
        for c in comparisons:
            writer.writerow([
                c.time.isoformat(),
                c.sensor_id,
                f"{c.esl_value:.{DECIMALS}f}",
                "" if c.calculated_value is None else f"{c.calculated_value:.{DECIMALS}f}",
                "" if c.delta is None else f"{c.delta:.{DECIMALS}f}",
                c.status,
            ])

    return target_file


def export_json(data: Dict[str, List[DataPoint]], target_file: Path) -> Path:
    """Schreibt alle Zählerstände in eine JSON-Datei: [{sensorId, data: [{ts, value}]}]."""
    target_file = Path(target_file)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(to_json_string(data))

    return target_file
