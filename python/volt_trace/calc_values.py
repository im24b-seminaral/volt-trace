from pathlib import Path
import os
from volt_trace.esl import load_esl_folder
from volt_trace.sdat import load_sdat_folder, parse_sdat_file
from volt_trace.analysis import remove_duplicates, sort_measured_values_by_time
from collections import defaultdict


import timeit






ROOT_DIR = Path(__file__).parent.parent.parent

sdat_path = ROOT_DIR / "XML-Files" / "SDAT-Files"
esl_path = ROOT_DIR / "XML-Files" / "ESL-Files"

num_sdat_files = len(os.listdir(sdat_path))
num_esl_files = len(os.listdir(esl_path))

print(f"Anzahl SDAT-Files: {num_sdat_files}")
print(f"Anzahl ESL-Files: {num_esl_files}")

def get_folder_size(folder_path):
    size = 0
    for path, dirs, files in os.walk(folder_path):
        for f in files:
            fp = os.path.join(path, f)
            size += os.path.getsize(fp)
    return size

def format_bytes(size):
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'kilo', 2: 'mega', 3: 'giga', 4: 'tera'}
    while size > power:
        size /= power
        n += 1
    return "{:.2f}".format(size) + " " + power_labels[n]+'bytes'

print(f"Grösse aller Files: {format_bytes(get_folder_size(sdat_path) + get_folder_size(esl_path))}")
laufzeit = timeit.timeit(lambda: load_sdat_folder(sdat_path), number=1)
print(f"Laufzeit SDAT-Files Parsen: {laufzeit} Sekunden")
sdat_roh = load_sdat_folder(sdat_path)
sdat_data = {
    sensor_id: remove_duplicates(sort_measured_values_by_time(werte))
    for sensor_id, werte in sdat_roh.items()
}


esl_data = load_esl_folder(esl_path)

for sensor_id, werte in sdat_data.items():
    print(f"sdat {sensor_id}: {len(werte)} Messwerte")

for sensor_id, werte in esl_data.items():
    print(f"ESL  {sensor_id}: {len(werte)} Zählerstände")


def find_conflicts(werte):
    """Zeitpunkte, zu denen mehrere Dateien UNTERSCHIEDLICHE Werte liefern."""
    pro_zeitpunkt = defaultdict(set)
    for messwert in werte:
        pro_zeitpunkt[messwert.timestamp].add(round(messwert.volume, 4))
    return {ts: werte_ for ts, werte_ in pro_zeitpunkt.items() if len(werte_) > 1}

konflikte_gesamt = 0
messpunkte_gesamt = 0

for sensor_id, werte in sdat_roh.items():
    konflikte = find_conflicts(werte)
    anzahl_eindeutig = len(sdat_data[sensor_id])
    konflikte_gesamt += len(konflikte)
    messpunkte_gesamt += anzahl_eindeutig
    print(f"{sensor_id}: {len(konflikte)} widersprüchliche Zeitpunkte "
          f"von {anzahl_eindeutig} ({len(konflikte)/anzahl_eindeutig*100:.0f} %)")

print(f"Gesamt: {konflikte_gesamt} von {messpunkte_gesamt} "
      f"({konflikte_gesamt/messpunkte_gesamt*100:.0f} %)")