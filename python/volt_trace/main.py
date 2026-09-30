"""
main.py - Haupteinstiegspunkt und Orchestrierung der Volt-Trace Pipeline.
"""

import argparse
from pathlib import Path

from volt_trace.esl import load_esl_folder
from volt_trace.export import (KIND_CONSUMPTION, KIND_METER, consumption_points,
                               export_csv, meter_points)
from volt_trace.sdat import load_sdat_folder


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
        help="Directory for CSV files",
    )
    args = parser.parse_args()

    sdat_data = load_sdat_folder(args.sdat_dir)
    esl_data = load_esl_folder(args.esl_dir)
    export_csv(consumption_points(sdat_data), args.output_dir, KIND_CONSUMPTION)
    export_csv(meter_points(esl_data), args.output_dir, KIND_METER)


if __name__ == "__main__":
    main()
