"""
export.py - Exportiert Zählerstände als CSV-Dateien.

Format (gemäss Aufgabenstellung):
- eine Datei pro Sensor, Dateiname = Sensor-ID (z. B. ID742.csv)
- Spalten: timestamp,value
- timestamp = Unix-Zeit in Sekunden (UTC), value = absoluter Zählerstand
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

DataPoint = Tuple[datetime, float]   # (Zeitpunkt, Zählerstand)


def export_csv(data: Dict[str, List[DataPoint]], target_folder: Path) -> List[Path]:
    """Schreibt eine CSV-Datei pro Sensor und gibt die Pfade der erstellten Dateien zurück."""
    target_folder = Path(target_folder)
    target_folder.mkdir(parents=True, exist_ok=True)
    created_files = []

    for sensor_id, points in data.items():
        file = target_folder / f"{sensor_id}.csv"
        with open(file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "value"])
            for time, value in sorted(points):
                writer.writerow([int(time.timestamp()), value])
        created_files.append(file)

    return created_files


