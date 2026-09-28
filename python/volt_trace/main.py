"""
main.py - Haupteinstiegspunkt und Orchestrierung der Volt-Trace Pipeline.
"""

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from volt_trace.analysis import MeterReading, calculate_meter_readings
from volt_trace.esl import EslMeterReading, parse_esl_file
from volt_trace.sdat import MeasuredValue, parse_sdat_file


def _merge_esl_readings(
    esl_paths: List[Path],
) -> Dict[str, List[EslMeterReading]]:
    merged: Dict[str, List[EslMeterReading]] = defaultdict(list)
    for path in esl_paths:
        for sensor_id, readings in parse_esl_file(path).items():
            merged[sensor_id].extend(readings)
    for sensor_id in merged:
        merged[sensor_id].sort(key=lambda reading: reading.start_time)
    return dict(merged)


def _latest_esl_before(
    readings: List[EslMeterReading], before: datetime
) -> EslMeterReading | None:
    candidates = [reading for reading in readings if reading.start_time <= before]
    if not candidates:
        return None
    return max(candidates, key=lambda reading: reading.start_time)


def run_pipeline(esl_dir: Path, sdat_dir: Path) -> Dict[str, List[MeterReading]]:
    esl_paths = sorted(esl_dir.glob("*.xml"))
    sdat_paths = sorted(sdat_dir.glob("*.xml"))

    esl_by_sensor = _merge_esl_readings(esl_paths)
    results: Dict[str, List[MeterReading]] = {}

    for sdat_path in sdat_paths:
        parsed = parse_sdat_file(sdat_path)
        if not parsed:
            continue
        sensor_id, measured_values = parsed
        if not measured_values:
            continue

        esl_readings = esl_by_sensor.get(sensor_id, [])
        reference = _latest_esl_before(esl_readings, measured_values[0].timestamp)
        if reference is None:
            continue

        results[sensor_id] = calculate_meter_readings(
            measured_values,
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
