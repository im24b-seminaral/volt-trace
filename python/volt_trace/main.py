"""
main.py - Haupteinstiegspunkt und Orchestrierung der Volt-Trace Pipeline.
"""

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from volt_trace.analysis import Zaehlerstand, berechne_zaehlerstand
from volt_trace.esl import parse_esl_file
from volt_trace.sdat import Messwert, parse_sdat_file


def _merge_esl_readings(
    esl_paths: List[Path],
) -> Dict[str, List[Zaehlerstand]]:
    merged: Dict[str, List[Zaehlerstand]] = defaultdict(list)
    for path in esl_paths:
        for sensor_id, readings in parse_esl_file(path).items():
            merged[sensor_id].extend(readings)
    for sensor_id in merged:
        merged[sensor_id].sort(key=lambda z: z.timestamp)
    return dict(merged)


def _latest_esl_before(
    readings: List[Zaehlerstand], before: datetime
) -> Zaehlerstand | None:
    candidates = [z for z in readings if z.timestamp <= before]
    if not candidates:
        return None
    return max(candidates, key=lambda z: z.timestamp)


def run_pipeline(esl_dir: Path, sdat_dir: Path) -> Dict[str, List[Zaehlerstand]]:
    esl_paths = sorted(esl_dir.glob("*.xml"))
    sdat_paths = sorted(sdat_dir.glob("*.xml"))

    esl_by_sensor = _merge_esl_readings(esl_paths)
    results: Dict[str, List[Zaehlerstand]] = {}

    for sdat_path in sdat_paths:
        parsed = parse_sdat_file(sdat_path)
        if not parsed:
            continue
        sensor_id, messwerte = parsed
        if not messwerte:
            continue

        esl_readings = esl_by_sensor.get(sensor_id, [])
        reference = _latest_esl_before(esl_readings, messwerte[0].timestamp)
        if reference is None:
            continue

        results[sensor_id] = berechne_zaehlerstand(
            messwerte,
            reference.value,
            reference.timestamp,
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="volt-trace SDAT/ESL pipeline")
    parser.add_argument(
        "--esl-dir",
        type=Path,
        required=True,
        help="Verzeichnis mit ESL-XML-Dateien",
    )
    parser.add_argument(
        "--sdat-dir",
        type=Path,
        required=True,
        help="Verzeichnis mit SDAT-XML-Dateien",
    )
    args = parser.parse_args()
    run_pipeline(args.esl_dir, args.sdat_dir)


if __name__ == "__main__":
    main()
