"""
csv_export.py - Export meter readings as CSV.

Format (as required by the assignment):
- one file per sensor, file name = sensor ID (e.g. ID742.csv)
- columns: timestamp,value
- timestamp = Unix time in seconds (UTC), value = absolute meter reading
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

DataPoint = Tuple[datetime, float]   # (time, meter reading)


def export_csv(data: Dict[str, List[DataPoint]], target_folder: Path) -> List[Path]:
    """Writes one CSV file per sensor. Returns the paths of the created files."""
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


