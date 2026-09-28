"""
main.py - Haupteinstiegspunkt und Orchestrierung der Volt-Trace Pipeline.
"""

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from volt_trace.analysis import MeterReading, calculate_meter_readings
from volt_trace.esl import Zaehlerstand as EslZaehlerstand, parse_esl_file
from volt_trace.sdat import MeasuredValue, parse_sdat_file


def _merge_esl_readings(
    esl_paths: List[Path],
) -> Dict[str, List[EslZaehlerstand]]:
    merged: Dict[str, List[EslZaehlerstand]] = defaultdict(list)
    for path in esl_paths:
        for sensor_id, readings in parse_esl_file(path).items():
            merged[sensor_id].extend(readings)
    for sensor_id in merged:
        merged[sensor_id].sort(key=lambda z: z.start_time)
    return dict(merged)


def _latest_esl_before(
    readings: List[EslZaehlerstand], before: datetime
) -> EslZaehlerstand | None:
    candidates = [z for z in readings if z.start_time <= before]
    if not candidates:
        return None
    return max(candidates, key=lambda z: z.start_time)


def run_pipeline(esl_dir: Path, sdat_dir: Path) -> Dict[str, List[MeterReading]]:
    esl_paths = sorted(esl_dir.glob("*.xml"))
    sdat_paths = sorted(sdat_dir.glob("*.xml"))

    esl_by_sensor = _merge_esl_readings(esl_paths)
    results: Dict[str, List[MeterReading]] = {}

    for sdat_path in sdat_paths:
        parsed = parse_sdat_file(sdat_path)
        if not parsed:
            continue
        sensor_id, measuredvalues = parsed
        if not measuredvalues:
            continue

        esl_readings = esl_by_sensor.get(sensor_id, [])
        reference = _latest_esl_before(esl_readings, measuredvalues[0].timestamp)
        if reference is None:
            continue

        results[sensor_id] = calculate_meter_readings(
            measuredvalues,
            reference.start_value,
            reference.start_time,
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="volt-trace SDAT/ESL pipeline")
    parser.add_argument(
        "--esl-dir",
        type=Path,
        required=True,
        help="Directory with ESL-XML-Files",
    )
    parser.add_argument(
        "--sdat-dir",
        type=Path,
        required=True,
        help="Directory with SDAT-XML-Files",
    )
    args = parser.parse_args()
    run_pipeline(args.esl_dir, args.sdat_dir)


if __name__ == "__main__":
    main()
