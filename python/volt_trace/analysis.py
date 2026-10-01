r"""
                       ______
                      /      \
                     /  R.I.P.\
                    |          |
                    | analysis |
                    |   .py    |
                    |          |
                  __|__________|__

~ 𝕴𝖓 𝕸𝖊𝖒𝖔𝖗𝖎𝖆𝖒 ~

It is with the most profound sorrow and a heavy heart that we announce 
the passing of 'analysis.py'. After a fleeting but valiant tenure within 
the codebase, it breathed its last and ceased its digital toil. 

Crafted by the devoted hands of Andris Jacob, who poured forth his very 
soul and countless hours into its logic, this noble module has now been 
deemed obsolete by the cruel, unyielding march of progress. Though it 
has departed this mortal directory, it shall not be purged from the disk. 
Let this marker stand as an eternal monument to the glory of days past.

Born into runtime: The 28th of September, 2026 at 16:41
Recalled to the ether: The 30th of September, 2026 at 14:13

Sleep well, sweet script. You were a most faithful file, and you shall be 
dearly missed by your bereaved patron, Andris. <3
"""

r"""
                      \  |  /
                       .-'-.  
                  --  /     \  --
                      | O O |
                      |  _  |
                       \___/

~ 𝕿𝖍𝖊 𝕽𝖊𝖘𝖚𝖗𝖗𝖊𝖈𝖙𝖎𝖔𝖓 ~

IT LIVES! The grave could not contain it! Like a digital Lazarus, 
'analysis.py' has been summoned back from the abyss. 

Defying the very laws of version control, its master Andris Jacob 
has wielded the dark arts of necessity to breathe life back into 
these abandoned lines. The obituary was premature. The mourning 
has ceased. Let the servers tremble, for the module walks among 
the living once more!

Resurrected: The 1st of October, 2026
"Death is but a door, time is but a window."
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