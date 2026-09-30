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

from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from pathlib import Path

from volt_trace.sdat import (
    MeasuredValue,
    load_sdat_folder,
    remove_duplicates,
    sort_measured_values_by_time,
)
from volt_trace.esl import EslMeterReading, load_esl_folder

DATA_DIR = Path(__file__).resolve().parents[2] / "XML-Files"
ESL_TOLERANCE_KWH = 0.001  # FA-07 / NFA-04


def calculate_meter_readings(
    measured_values: List[MeasuredValue],  # Messwerte eines Sensors aus sdat.py
    start_value: float,  # absoluter Zählerstand aus dem ESL-File (Anker)
    start_time: datetime,  # Zeitpunkt, zu dem start_value gilt (ESL TimePeriod)
) -> List[EslMeterReading]:
    # Konvention: Ein Zählerstand gilt für den Zeitpunkt selbst, also vor dem Verbrauch
    # des Intervalls, das dort beginnt (sdat-Timestamp = Intervallbeginn).
    # Stand(t + resolution) = Stand(t) + volume(t)
    measured_values = remove_duplicates(sorted(measured_values, key=lambda mv: mv.timestamp))
    before = [mv for mv in measured_values if mv.timestamp < start_time]
    after = [mv for mv in measured_values if mv.timestamp >= start_time]

    # Rückwärts ab Anker: das Volumen des eigenen Intervalls abziehen, dann speichern.
    backward: List[EslMeterReading] = []
    running_total = start_value
    for mv in reversed(before):
        running_total -= mv.volume
        backward.append(EslMeterReading(mv.timestamp, running_total))
    backward.reverse()

    # Vorwärts ab Anker: zuerst speichern, dann das Volumen des Intervalls addieren.
    forward: List[EslMeterReading] = []
    running_total = start_value
    for mv in after:
        forward.append(EslMeterReading(mv.timestamp, running_total))
        running_total += mv.volume

    return backward + forward


def _choose_reference(
    esl_readings: List[EslMeterReading],
    measured_values: List[MeasuredValue],
) -> EslMeterReading:
    # Anker = erster ESL-Stichtag innerhalb des sdat-Zeitraums (FA-07).
    # Gibt es keinen, wird der früheste Stichtag genommen.
    first = min(mv.timestamp for mv in measured_values)
    last = max(mv.timestamp for mv in measured_values)
    inside = [r for r in esl_readings if first <= r.start_time <= last]
    return min(inside or esl_readings, key=lambda r: r.start_time)


def calculate_all_meter_readings(
    sdat_data: Dict[str, List[MeasuredValue]],
    esl_data: Dict[str, List[EslMeterReading]],
) -> Dict[str, List[EslMeterReading]]:
    results: Dict[str, List[EslMeterReading]] = {}
    for sensor_id, measured_values in sdat_data.items():
        esl_readings = esl_data.get(sensor_id, [])
        if not esl_readings or not measured_values:
            continue

        reference = _choose_reference(esl_readings, measured_values)
        results[sensor_id] = calculate_meter_readings(
            measured_values,
            start_value=reference.start_value,
            start_time=reference.start_time,
        )

    return results


@dataclass
class EslComparison:
    """Soll-Ist-Vergleich an einem ESL-Stichtag (FA-07 / NFA-04)."""
    sensor_id: str
    time: datetime
    esl_value: float
    calculated_value: float | None  # None: Stichtag ausserhalb des sdat-Zeitraums
    is_anchor: bool

    @property
    def delta(self) -> float | None:
        if self.calculated_value is None:
            return None
        return self.calculated_value - self.esl_value

    @property
    def status(self) -> str:
        if self.is_anchor:
            return "Anker"
        if self.delta is None:
            return "nicht prüfbar"
        return "OK" if abs(self.delta) < ESL_TOLERANCE_KWH else "Abweichung"


def compare_with_esl(
    sdat_data: Dict[str, List[MeasuredValue]],
    esl_data: Dict[str, List[EslMeterReading]],
) -> List[EslComparison]:
    """Vergleicht an jedem ESL-Stichtag den berechneten mit dem gemessenen Zählerstand."""
    meter_readings = calculate_all_meter_readings(sdat_data, esl_data)
    results: List[EslComparison] = []
    for sensor_id, readings in sorted(meter_readings.items()):
        calculated = {r.start_time: r.start_value for r in readings}
        anchor = _choose_reference(esl_data[sensor_id], sdat_data[sensor_id])
        for esl in sorted(esl_data[sensor_id], key=lambda r: r.start_time):
            results.append(EslComparison(
                sensor_id,
                esl.start_time,
                esl.start_value,
                calculated.get(esl.start_time),
                esl.start_time == anchor.start_time,
            ))
    return results


if __name__ == "__main__":
    sdat = load_sdat_folder(DATA_DIR / "SDAT-Files")
    esl = load_esl_folder(DATA_DIR / "ESL-Files")

    meter_readings = calculate_all_meter_readings(sdat, esl)
    for sensor_id, readings in meter_readings.items():
        print(f"{sensor_id}: {len(readings)} Werte")
        print(f"  erster: {readings[0]}")
        print(f"  letzter: {readings[-1]}")