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

if __name__ == "__main__":
    from sdat import load_sdat_folder
    from esl import load_esl_folder
    from analysis import calculate_all_meter_readings

    base = Path(__file__).parent                      # = volt_trace
    xml_folder = base / "XML-Files (1)"

    sdat = load_sdat_folder(xml_folder / "SDAT-Files")
    esl = load_esl_folder(xml_folder / "ESL-Files")
    readings = calculate_all_meter_readings(sdat, esl)

    data = {
        sensor_id: [(r.start_time, r.start_value) for r in values]
        for sensor_id, values in readings.items()
    }

    for file in export_csv(data, base / "export"):
        lines = file.read_text(encoding="utf-8").splitlines()
        print(f"{file.name}: {len(lines) - 1} rows")
        for line in lines[:3]:
            print("  " + line)