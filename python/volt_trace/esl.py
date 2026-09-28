"""
esl.py - Einlesen und Parsen von ESL-XML-Dateien.

Zweck und Aufgaben dieser Datei:
--------------------------------
1. Einlesen von ESL-XML-Dateien (absolute Zählerstände, meist monatlich).
2. Extrahieren der relevanten XML-Knoten:
   - <TimePeriod end="...">: Ablesezeitpunkt (Lokalzeit Europe/Zurich, ohne "Z")
   - <ValueRow obis="..." value="...">: Zählerstand pro OBIS-Code
     * ID742 Netzbezug:   1-1:1.8.1 (Hochtarif) + 1-1:1.8.2 (Niedertarif)
     * ID735 Einspeisung: 1-1:2.8.1 (Hochtarif) + 1-1:2.8.2 (Niedertarif)
     * alle anderen OBIS-Codes (und andere Zähler) werden ignoriert
3. Bereitstellung von Datenklassen für absolute Zählerstände:
   - Umrechnung der Lokalzeit in UTC (gleich wie sdat.py).
   - Summe aus Hoch- und Niedertarif = effektiver Zählerstand.
   - Rückgabe strukturierter Messreihen zur Weiterverarbeitung in analysis.py.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ESL_TIMEZONE = ZoneInfo("Europe/Zurich")
TARIFF_REGISTERS = ("1", "2")
OBIS_GROUP_TO_SENSOR = {
    "1-1:1.8": "ID742",
    "1-1:2.8": "ID735",
}


def _obis_group(obis: str) -> str | None:
    """OBIS-Basis ohne Tarifregister (.1 Hochtarif, .2 Niedertarif)."""
    prefix, register = obis.rsplit(".", 1)
    if register in TARIFF_REGISTERS:
        return prefix
    return None


def _total_readings_by_obis_group(values: Dict[str, float]) -> Dict[str, float]:
    """Summiert Hoch- und Niedertarif je OBIS-Gruppe, wenn beide Register vorhanden."""
    by_group: Dict[str, Dict[str, float]] = {}
    for obis, value in values.items():
        group = _obis_group(obis)
        if group is None:
            continue
        register = obis.rsplit(".", 1)[1]
        by_group.setdefault(group, {})[register] = value

    totals: Dict[str, float] = {}
    for group, register_values in by_group.items():
        if all(register in register_values for register in TARIFF_REGISTERS):
            totals[group] = round(
                register_values["1"] + register_values["2"], 4
            )
    return totals


@dataclass
class EslMeterReading:
    start_time: datetime   # Ablesezeitpunkt in UTC
    start_value: float     # absoluter Zählerstand in kWh (HT + NT)


def _get_attribute(element, name) -> str:
    value = element.get(name)
    if value is None:
        raise ValueError(f"Attribute not found: {name}")
    return value


def _parse_start_time(value) -> datetime:
    local_time = datetime.fromisoformat(value).replace(tzinfo=ESL_TIMEZONE)
    return local_time.astimezone(timezone.utc)


def _parse_value_rows(time_period) -> Dict[str, float]:
    return {
        _get_attribute(row, "obis"): float(_get_attribute(row, "value"))
        for row in time_period.iter("ValueRow")
    }


def parse_esl_file(file_path: Path) -> Dict[str, List[EslMeterReading]]:
    """Liest ein ESL-File ein. Gibt {sensor_id: [Zaehlerstaende]} zurück.
    Ein ESL-File enthält beide Sensoren, deshalb kommen bis zu zwei Einträge zurück."""
    root = ET.parse(file_path).getroot()
    result: Dict[str, List[EslMeterReading]] = {
        sensor_id: [] for sensor_id in OBIS_GROUP_TO_SENSOR.values()
    }

    for time_period in root.iter("TimePeriod"):
        start_time = _parse_start_time(_get_attribute(time_period, "end"))
        values = _parse_value_rows(time_period)
        totals = _total_readings_by_obis_group(values)

        for group, start_value in totals.items():
            sensor_id = OBIS_GROUP_TO_SENSOR.get(group)
            if sensor_id is not None:
                result[sensor_id].append(EslMeterReading(start_time, start_value))

    return {sensor_id: values for sensor_id, values in result.items() if values}

def load_esl_folder(folder_path: Path) -> Dict[str, List[EslMeterReading]]:
    alle_zaehlerstaende: Dict[str, List[EslMeterReading]] = {}
    for xml_file in folder_path.glob("*.xml"):
        for sensor_id, zaehlerstaende in parse_esl_file(xml_file).items():
            alle_zaehlerstaende.setdefault(sensor_id, []).extend(zaehlerstaende)
    return alle_zaehlerstaende