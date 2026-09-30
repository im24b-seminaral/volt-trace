import argparse
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
                   for p in sorted(points, key=lambda p: p.time)]
        return cls(sensor_id, entries)


def _check_sensor_id(sensor_id: str) -> str:
    if not SENSOR_ID_PATTERN.match(sensor_id):
        raise ValueError(f"Ungültige Sensorkennung: {sensor_id!r}")
    return sensor_id


def to_csv_string(points: List[DataPoint]) -> str:
    """Gibt die Zählerstände eines Sensors als CSV-Text zurück (timestamp,value)."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["timestamp", "value"])
    for p in sorted(points, key=lambda p: p.time):
        writer.writerow([p.to_unix(), f"{p.value:.{DECIMALS}f}"])
    return buffer.getvalue()


def to_json_payload(data: Dict[str, List[DataPoint]]) -> list:
    """Baut das Format [{sensorId, data: [{ts, value}]}] für JSON-Datei und HTTP POST."""
    return [asdict(SensorExport.from_points(_check_sensor_id(sid), pts))
            for sid, pts in sorted(data.items())]


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


def export_json(data: Dict[str, List[DataPoint]], target_file: Path) -> Path:
    """Schreibt alle Zählerstände als JSON-Array: [{sensorId, data: [{ts, value}]}]."""
    target_file = Path(target_file)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(to_json_payload(data), f, indent=2)

    return target_file


def main() -> None:
    from volt_trace.analysis import calculate_all_meter_readings
    from volt_trace.esl import load_esl_folder
    from volt_trace.sdat import load_sdat_folder

    parser = argparse.ArgumentParser(description="Exportiert Zählerstände als CSV und JSON")
    parser.add_argument("--sdat-dir", type=Path, required=True, help="Ordner mit sdat-Files")
    parser.add_argument("--esl-dir", type=Path, required=True, help="Ordner mit ESL-Files")
    parser.add_argument("--output-dir", type=Path, default=Path("export"), help="Zielordner")
    args = parser.parse_args()

    readings = calculate_all_meter_readings(
        load_sdat_folder(args.sdat_dir),
        load_esl_folder(args.esl_dir),
    )
    data = {
        sensor_id: [DataPoint(r.start_time, r.start_value) for r in values]
        for sensor_id, values in readings.items()
    }

    for file in export_csv(data, args.output_dir):
        print(f"CSV:  {file}")
    print(f"JSON: {export_json(data, args.output_dir / 'meter_readings.json')}")


if __name__ == "__main__":
    main()
