"""
calc_values.py - Key figures for the project documentation.

Run from the "python" folder:
    python -m volt_trace.calc_values
"""

import os
import time
from collections import defaultdict
from pathlib import Path

from volt_trace.analysis import remove_duplicates, sort_measured_values_by_time
from volt_trace.sdat import load_sdat_folder, parse_sdat_file

from volt_trace.esl import EslMeterReading, load_esl_folder
from volt_trace.compare_esl_vs_sdat import compare_esl_sdat

ROOT_DIR = Path(__file__).parent.parent.parent
SDAT_PATH = ROOT_DIR / "XML-Files" / "SDAT-Files"
ESL_PATH = ROOT_DIR / "XML-Files" / "ESL-Files"


def count_conflicts(measured_values):
    per_timestamp = defaultdict(set)
    for measured_value in measured_values:
        per_timestamp[measured_value.timestamp].add(round(measured_value.volume, 4))
    return sum(1 for values in per_timestamp.values() if len(values) > 1)


num_sdat_files = len(os.listdir(SDAT_PATH))
num_esl_files = len(os.listdir(ESL_PATH))
megabytes = sum(f.stat().st_size for f in [*SDAT_PATH.iterdir(), *ESL_PATH.iterdir()]) / 1000 / 1000

start = time.perf_counter()
sdat_raw = load_sdat_folder(SDAT_PATH)
parse_runtime = time.perf_counter() - start

sdat_data = {
    sensor_id: remove_duplicates(sort_measured_values_by_time(values))
    for sensor_id, values in sdat_raw.items()
}

measurements = sum(len(values) for values in sdat_data.values())
conflicts = sum(count_conflicts(values) for values in sdat_raw.values())

def count_zero_in_older_file(sdat_path):
    """Share of conflicts where the oldest file delivered 0.000."""
    per_timestamp = defaultdict(list)
    # the file name starts with the date, so sorted() = oldest first
    for xml_file in sorted(sdat_path.glob("*.xml")):
        for sensor_id, values in parse_sdat_file(xml_file).items():
            for value in values:
                per_timestamp[(sensor_id, value.timestamp)].append((xml_file.name, value.volume))

    conflicts = [entries for entries in per_timestamp.values()
                 if len({round(volume, 4) for _name, volume in entries}) > 1]
    zero_first = sum(1 for entries in conflicts if round(min(entries)[1], 4) == 0.0)
    return zero_first / len(conflicts) * 100

def deduplicate_newest_wins(sdat_path):
    """Per timestamp the value from the newest file (older files often hold 0.000)."""
    per_timestamp = defaultdict(list)
    for xml_file in sorted(sdat_path.glob("*.xml")):
        for sensor_id, values in parse_sdat_file(xml_file).items():
            for value in values:
                per_timestamp[(sensor_id, value.timestamp)].append((xml_file.name, value))

    per_sensor = defaultdict(list)
    for (sensor_id, _timestamp), entries in per_timestamp.items():
        per_sensor[sensor_id].append(max(entries, key=lambda e: e[0])[1])
    return per_sensor

def compare_with_esl(measured_values, meter_readings):
    """Intervals between two ESL dates, without the unusable ones."""
    intervals = compare_esl_sdat(measured_values, meter_readings)
    last_measurement = max(value.timestamp for value in measured_values)
    return [i for i in intervals
            if i["esl_diff"] and i["sdat_summe"] and i["bis"] <= last_measurement]

# Swiss thousands separator: 258232 -> 258'232
sdat_files_text = f"{num_sdat_files:,}".replace(",", "'")
measurements_text = f"{measurements:,}".replace(",", "'")
conflicts_text = f"{conflicts:,}".replace(",", "'")

esl_data = load_esl_folder(ESL_PATH)

measurements_per_sensor = deduplicate_newest_wins(SDAT_PATH)
usable = compare_with_esl(measurements_per_sensor["ID742"], esl_data["ID742"])
exact = [i for i in usable if abs(i["sdat_summe"] - 3 * i["esl_diff"]) < 0.05]

deviating = [i for i in usable if abs(i["sdat_summe"] - 3 * i["esl_diff"]) >= 1]
deviation_kwh = sum(abs(i["sdat_summe"] - 3 * i["esl_diff"]) for i in deviating) / 3


print(f"Gelieferte Files: {sdat_files_text} sdat, {num_esl_files} ESL, rund {megabytes:.0f} MB")
print(f"Messpunkte nach Deduplizierung: {measurements_text}")
print(f"Zeitpunkte mit widersprüchlichen Werten: {conflicts_text}, "
      f"rund {conflicts / measurements * 100:.0f} Prozent")
print(f"Davon mit 0.000 im älteren File: {count_zero_in_older_file(SDAT_PATH)}")
print(f"Laufzeit Parsen aller sdat-Files: {parse_runtime:.1f} Sekunden")
print(f"Verhältnis sdat-Summe zu ESL-Differenz: "
      f"Faktor 3, in {len(exact)} von {len(usable)} Intervallen exakt")
print(f"Zusätzliche Abweichung in {len(deviating)} Monaten: "
          f"rund {deviation_kwh:.0f} kWh")