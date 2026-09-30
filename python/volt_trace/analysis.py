"""
analysis.py - Datenaggregation, Verknüpfung und Zählerstandsberechnung.

Zweck und Aufgaben dieser Datei:
--------------------------------
1. Datenmodell «Messwert» (NFA-02): Klasse MeterReading mit
     * timestamp: Zeitstempel in UTC (Intervallende, dient als Schlüssel)
     * consumption: Verbrauchswert aus sdat im Intervall ab timestamp
     * meter_value: Berechneter absoluter Zählerstand zu diesem Zeitpunkt
2. Duplikatbehandlung und Sortierung:
   - Ablage pro Sensor als MeterSeries = dict[datetime, MeterReading].
   - Invariante (eindeutig, aufsteigend sortiert, UTC) wird von check_series geprüft.
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
from datetime import datetime, timedelta
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


@dataclass
class MeterReading:
    """Messwert (NFA-02): Verbrauch und Zählerstand eines Sensors zu einem Zeitpunkt."""
    timestamp: datetime   # UTC, Ende des Intervalls (Beginn, Ende]
    consumption: float    # Verbrauch im Intervall mit diesem Ende (kWh, aus sdat)
    meter_value: float    # Zählerstand am Ende des Intervalls (kWh, berechnet)


# Zeitreihe eines Sensors. Ein dict garantiert eindeutige Schlüssel und behält die
# Einfügereihenfolge; check_series belegt, dass diese aufsteigend und in UTC ist.
MeterSeries = Dict[datetime, MeterReading]


def check_series(series: MeterSeries) -> None:
    """Prüft die Invariante von NFA-02: Schlüssel = timestamp, UTC, streng aufsteigend."""
    previous = None
    for key, reading in series.items():
        if key != reading.timestamp:
            raise ValueError(f"Schlüssel {key} passt nicht zum Messwert {reading.timestamp}")
        if key.utcoffset() != timedelta(0):
            raise ValueError(f"Zeitstempel nicht in UTC: {key}")
        if previous is not None and key <= previous:
            raise ValueError(f"Zeitstempel nicht aufsteigend: {previous} -> {key}")
        previous = key


def calculate_meter_readings(
    measured_values: List[MeasuredValue],  # Messwerte eines Sensors aus sdat.py
    start_value: float,  # absoluter Zählerstand aus dem ESL-File (Anker)
    start_time: datetime,  # Zeitpunkt, zu dem start_value gilt (ESL TimePeriod)
) -> MeterSeries:
    # sdat-Timestamp = Intervallende; ESL-Anker = Zählerstand am Ende des ESL-Intervalls.
    measured_values = remove_duplicates(sorted(measured_values, key=lambda mv: mv.timestamp))
    before = [mv for mv in measured_values if mv.timestamp < start_time]
    at_anchor = [mv for mv in measured_values if mv.timestamp == start_time]
    after = [mv for mv in measured_values if mv.timestamp > start_time]

    backward: List[MeterReading] = []
    running_total = start_value
    for mv in reversed(before):
        running_total -= mv.volume
        backward.append(MeterReading(mv.timestamp, mv.volume, running_total))
    backward.reverse()

    anchor_readings = [
        MeterReading(mv.timestamp, mv.volume, start_value) for mv in at_anchor
    ]

    forward: List[MeterReading] = []
    running_total = start_value
    for mv in after:
        running_total += mv.volume
        forward.append(MeterReading(mv.timestamp, mv.volume, running_total))

    series = {reading.timestamp: reading for reading in backward + anchor_readings + forward}
    check_series(series)
    return series


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
) -> Dict[str, MeterSeries]:
    results: Dict[str, MeterSeries] = {}
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
    for sensor_id, series in sorted(meter_readings.items()):
        anchor = _choose_reference(esl_data[sensor_id], sdat_data[sensor_id])
        for esl in sorted(esl_data[sensor_id], key=lambda r: r.start_time):
            reading = series.get(esl.start_time)
            results.append(EslComparison(
                sensor_id,
                esl.start_time,
                esl.start_value,
                None if reading is None else reading.meter_value,
                esl.start_time == anchor.start_time,
            ))
    return results


if __name__ == "__main__":
    sdat = load_sdat_folder(DATA_DIR / "SDAT-Files")
    esl = load_esl_folder(DATA_DIR / "ESL-Files")

    meter_readings = calculate_all_meter_readings(sdat, esl)
    for sensor_id, series in meter_readings.items():
        readings = list(series.values())
        print(f"{sensor_id}: {len(readings)} Werte")
        print(f"  erster: {readings[0]}")
        print(f"  letzter: {readings[-1]}")