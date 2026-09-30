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

from volt_trace.quantities import round_kwh
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
            totals[group] = round_kwh(register_values["1"] + register_values["2"])
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


VALID_STATUS = "V"

def _parse_value_rows(time_period, invalid_rows: List | None = None) -> Dict[str, float]:
    values: Dict[str, float] = {}
    for row in time_period.iter("ValueRow"):
        if row.get("status", VALID_STATUS) != VALID_STATUS:
            if invalid_rows is not None:
                invalid_rows.append(row)
            continue
        values[_get_attribute(row, "obis")] = float(_get_attribute(row, "value"))
    return values

def remove_esl_duplicates(esl_readings: List[EslMeterReading]) -> List[EslMeterReading]:
    unique: List[EslMeterReading] = []
    seen_timestamps = set()
    for reading in esl_readings:
        if reading.start_time not in seen_timestamps:
            unique.append(reading)
            seen_timestamps.add(reading.start_time)
    return unique

def parse_esl_file(file_path: Path, skipped: List[dict] | None = None, invalid_rows: List | None = None):
    root = ET.parse(file_path).getroot()
    result: Dict[str, List[EslMeterReading]] = {
        sensor_id: [] for sensor_id in OBIS_GROUP_TO_SENSOR.values()
    }
    group_owner: Dict[str, str] = {}   # OBIS-Gruppe -> factoryNo des liefernden Meters

    for meter in root.iter("Meter"):
        factory_no = meter.get("factoryNo") or "unbekannt"
        used = False
        reason = "keine vollständigen OBIS-Paare (Hoch- und Niedertarif)"

        for time_period in meter.iter("TimePeriod"):
            start_time = _parse_start_time(_get_attribute(time_period, "end"))
            totals = _total_readings_by_obis_group(_parse_value_rows(time_period, invalid_rows))

            for group, start_value in totals.items():
                sensor_id = OBIS_GROUP_TO_SENSOR.get(group)
                if sensor_id is None:
                    continue
                owner = group_owner.setdefault(group, factory_no)
                if owner != factory_no:
                    reason = f"OBIS-Gruppe {group} wird bereits von Meter {owner} geliefert"
                    continue
                result[sensor_id].append(EslMeterReading(start_time, start_value))
                used = True

        if not used and skipped is not None:
            skipped.append({"meter": factory_no, "file": file_path.name, "reason": reason})

    return {sensor_id: values for sensor_id, values in result.items() if values}

def load_esl_folder(folder_path: Path, skipped: List[dict] | None = None):
    all_readings: Dict[str, List[EslMeterReading]] = {}
    for xml_file in sorted(folder_path.glob("*.xml")):
        file_skips: List[dict] = []
        invalid_rows: List = []
        try:
            readings = parse_esl_file(xml_file, file_skips, invalid_rows)
        except (ET.ParseError, ValueError, OSError) as error:
            if skipped is not None:
                reason = ("Kein gültiges XML" if isinstance(error, ET.ParseError)
                          else f"Fehlerhafte Daten: {error}")
                skipped.append({"file": xml_file.name, "reason": reason, "skippedRecords": 0})
            continue
        if skipped is not None:
            skipped.extend(file_skips)
            if invalid_rows:
                skipped.append({"file": xml_file.name, "reason": 'ValueRow mit status != "V"',
                                "skippedRecords": len(invalid_rows)})
        for sensor_id, values in readings.items():
            all_readings.setdefault(sensor_id, []).extend(values)
    return {
        sensor_id: sorted(remove_esl_duplicates(readings), key=lambda r: r.start_time)
        for sensor_id, readings in all_readings.items()
    }