"""
main.py - Haupteinstiegspunkt und Orchestrierung der Volt-Trace Pipeline.
"""

import argparse
from pathlib import Path
from typing import Dict

from volt_trace.analysis import MeterSeries, calculate_all_meter_readings
from volt_trace.esl import load_esl_folder
from volt_trace.export import DataPoint, export_csv, export_json
from volt_trace.sdat import load_sdat_folder


def run_pipeline(esl_dir: Path, sdat_dir: Path) -> Dict[str, MeterSeries]:
    sdat_data = load_sdat_folder(sdat_dir)
    esl_data = load_esl_folder(esl_dir)
    return calculate_all_meter_readings(sdat_data, esl_data)


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
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("export"),
        help="Directory for CSV and JSON files",
    )
    args = parser.parse_args()

    readings = run_pipeline(args.esl_dir, args.sdat_dir)
    data = {
        sensor_id: [DataPoint(r.timestamp, r.meter_value) for r in series.values()]
        for sensor_id, series in readings.items()
    }
    export_csv(data, args.output_dir)
    export_json(data, args.output_dir / "meter_readings.json")


if __name__ == "__main__":
    main()
