"""
analysis.py - Datenaggregation, Verknüpfung und Zählerstandsberechnung.

Zweck und Aufgaben dieser Datei:
--------------------------------
1. Datenmodell «Messwert»:
   - Speicherung von:
     * timestamp: Eindeutiger Zeitstempel in UTC (dient als Primärschlüssel / Key)
     * relative_value: Relativer Verbrauchswert aus sdat (z. B. in 15-Minuten-Intervallen)
     * absolute_value: Berechneter absoluter Zählerstand zu diesem Zeitpunkt
2. Duplikatbehandlung und Sortierung:
   - Zusammenführen von Messwerten in einer sortierten, duplikatfreien Datenstruktur
     (z. B. Dict sortiert nach Timestamp oder pandas.DataFrame mit Timestamp-Index).
3. Verrechnung von ESL- und SDAT-Daten:
   - Verbinden der relativen SDAT-Verbrauchswerte mit den absoluten ESL-Stichtagszählerständen:
     * ID735 (Einspeisung) & ID742 (Netzbezug).
   - Fortlaufende Aufsummierung der relativen Werte ausgehend vom Referenz-Zählerstand,
     um den exakten absoluten Zählerstand zu jedem Zeitstempel zu bestimmen.
4. Analyse- & Auswertungsfunktionen:
   - Vorbereitung aggregierter Daten für Verbrauchsdiagramme (Verbrauch pro Intervall / Tag).
   - Vorbereitung aggregierter Daten für Zählerstandsdiagramme (kontinuierlicher Verlauf).
"""

from typing import List, Dict
from datetime import datetime
from pathlib import Path

# pyrefly: ignore [missing-import]
from volt_trace.sdat import MeasuredValue, load_sdat_folder

# pyrefly: ignore [missing-import]
from volt_trace.esl import EslMeterReading, load_esl_folder

def sort_measured_values_by_time(measured_values: List[MeasuredValue]) -> List[MeasuredValue]:
    measured_values.sort(key=lambda value: value.timestamp)
    return measured_values


def remove_duplicates(measured_values: List[MeasuredValue]) -> List[MeasuredValue]:
    unique_measured_values: List[MeasuredValue] = []
    seen_timestamps = set()
    for measured_value in measured_values:
        if measured_value.timestamp not in seen_timestamps:
            unique_measured_values.append(measured_value)
            seen_timestamps.add(measured_value.timestamp)
    return unique_measured_values

def calculate_meter_readings(
    measured_values: List[MeasuredValue],  # sortierte, duplikatfreie Liste aus sdat.py
    start_value: float,  # absoluter Zählerstand aus dem ESL-File
    start_time: datetime,  # Zeitpunkt, zu dem start_value gilt (ESL TimePeriod)
) -> List[EslMeterReading]:

    measured_values = [mv for mv in measured_values if mv.timestamp >= start_time]
    measured_values = sort_measured_values_by_time(measured_values)
    measured_values = remove_duplicates(measured_values)
    running_total = start_value
    results: List[EslMeterReading] = []

    for mv in measured_values:
        running_total += mv.volume
        results.append(EslMeterReading(mv.timestamp, running_total))
    return results


def calculate_all_meter_readings(
    sdat_data: Dict[str, List[MeasuredValue]],
    esl_data: Dict[str, List[EslMeterReading]],
) -> Dict[str, List[EslMeterReading]]:
    results: Dict[str, List[EslMeterReading]] = {}
    for sensor_id, measured_values in sdat_data.items():
        esl_readings = esl_data.get(sensor_id, [])
        if not esl_readings:
            continue

        reference = min(esl_readings, key=lambda reading: reading.start_time)
        results[sensor_id] = calculate_meter_readings(
            measured_values,
            start_value=reference.start_value,
            start_time=reference.start_time,
        )

    return results
    

if __name__ == "__main__":
    sdat = load_sdat_folder(Path("C:\\volt-trace\\XML-Files\\SDAT-Files"))
    esl = load_esl_folder(Path("C:\\volt-trace\\XML-Files\\ESL-Files"))

    meter_readings = calculate_all_meter_readings(sdat, esl)
    for sensor_id, readings in meter_readings.items():
        print(f"{sensor_id}: {len(readings)} Werte")
        print(f"  erster: {readings[0]}")
        print(f"  letzter: {readings[-1]}")
