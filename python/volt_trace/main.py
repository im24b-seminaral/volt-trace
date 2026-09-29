"""
main.py - Haupteinstiegspunkt und Orchestrierung der Volt-Trace Pipeline.
"""

import argparse
from pathlib import Path
from typing import Dict, List

from volt_trace.analysis import calculate_all_meter_readings
from volt_trace.esl import EslMeterReading, load_esl_folder
from volt_trace.export import export_csv, export_json
from volt_trace.sdat import load_sdat_folder


def run_pipeline(esl_dir: Path, sdat_dir: Path) -> Dict[str, List[EslMeterReading]]:
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
        sensor_id: [(reading.start_time, reading.start_value) for reading in values]
        for sensor_id, values in readings.items()
    }
    export_csv(data, args.output_dir)
    export_json(data, args.output_dir)


if __name__ == "__main__":
    main()
