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
    source: "EslSource | None" = None


@dataclass(frozen=True)
class EslValueRow:
    obis: str | None
    value: str | None
    status: str


@dataclass(frozen=True)
class EslSource:
    file: str
    factory_no: str
    time_period_end: str
    rows: tuple[EslValueRow, ...]


class EslDataset(dict[str, List[EslMeterReading]]):
    def __init__(self, values: Dict[str, List[EslMeterReading]], sources: List[EslSource]):
        super().__init__(values)
        self.sources = sources


def _get_attribute(element, name) -> str:
    value = element.get(name)
    if value is None:
        raise ValueError(f"Attribute not found: {name}")
    return value


def _parse_start_time(value) -> datetime:
    local_time = datetime.fromisoformat(value).replace(tzinfo=ESL_TIMEZONE)
    return local_time.astimezone(timezone.utc)


VALID_STATUS = "V"

def _parse_value_rows(time_period, invalid_rows: List | None = None,
                      source_rows: List[EslValueRow] | None = None,
                      file_name: str = "", factory_no: str = "") -> Dict[str, float]:
    values: Dict[str, float] = {}
    for row in time_period.iter("ValueRow"):
        status = row.get("status", VALID_STATUS)
        if source_rows is not None:
            source_rows.append(EslValueRow(row.get("obis"), row.get("value"), status))
        if status != VALID_STATUS:
            if invalid_rows is not None:
                invalid_rows.append({"file": file_name, "meter": factory_no,
                                     "kind": "record", "obis": row.get("obis"),
                                     "status": status, "reason": f'ValueRow mit status "{status}"',
                                     "skippedRecords": 1})
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

def parse_esl_file(file_path: Path, skipped: List[dict] | None = None,
                   invalid_rows: List | None = None, source_path: str | None = None,
                   sources: List[EslSource] | None = None):
    root = ET.parse(file_path).getroot()
    source_path = source_path or file_path.name
    result: Dict[str, List[EslMeterReading]] = {
        sensor_id: [] for sensor_id in OBIS_GROUP_TO_SENSOR.values()
    }
    group_owner: Dict[str, str] = {}   # OBIS-Gruppe -> factoryNo des liefernden Meters

    for meter in root.iter("Meter"):
        factory_no = meter.get("factoryNo") or "unbekannt"
        used = False
        reason = "keine vollständigen OBIS-Paare (Hoch- und Niedertarif)"

        for time_period in meter.iter("TimePeriod"):
            end_text = _get_attribute(time_period, "end")
            start_time = _parse_start_time(end_text)
            source_rows: List[EslValueRow] = []
            totals = _total_readings_by_obis_group(_parse_value_rows(
                time_period, invalid_rows, source_rows, source_path, factory_no))
            source = EslSource(source_path, factory_no, end_text, tuple(source_rows))
            if sources is not None:
                sources.append(source)

            for group, start_value in totals.items():
                sensor_id = OBIS_GROUP_TO_SENSOR.get(group)
                if sensor_id is None:
                    continue
                owner = group_owner.setdefault(group, factory_no)
                if owner != factory_no:
                    reason = f"OBIS-Gruppe {group} wird bereits von Meter {owner} geliefert"
                    continue
                result[sensor_id].append(EslMeterReading(start_time, start_value, source))
                used = True

        if not used and skipped is not None:
            skipped.append({"meter": factory_no, "file": source_path,
                            "kind": "meter", "reason": reason, "skippedRecords": 0})

    return {sensor_id: values for sensor_id, values in result.items() if values}

def load_esl_folder(folder_path: Path, skipped: List[dict] | None = None):
    all_readings: Dict[str, List[EslMeterReading]] = {}
    sources: List[EslSource] = []
    for xml_file in sorted(path for path in folder_path.rglob("*")
                           if path.is_file() and path.suffix.lower() == ".xml"):
        source_path = xml_file.relative_to(folder_path).as_posix()
        file_skips: List[dict] = []
        invalid_rows: List = []
        try:
            file_sources: List[EslSource] = []
            readings = parse_esl_file(xml_file, file_skips, invalid_rows, source_path, file_sources)
        except (ET.ParseError, ValueError, OSError) as error:
            if skipped is not None:
                reason = ("Kein gültiges XML" if isinstance(error, ET.ParseError)
                          else f"Fehlerhafte Daten: {error}")
                skipped.append({"file": source_path, "kind": "file",
                                "reason": reason, "skippedRecords": 0})
            continue
        sources.extend(file_sources)
        if skipped is not None:
            skipped.extend(file_skips)
            skipped.extend(invalid_rows)
        if not any(readings.values()):
            if skipped is not None:
                skipped.append({"file": source_path, "kind": "file",
                                "reason": "Keine gültigen ESL-Zählerstände", "skippedRecords": 0})
            continue
        for sensor_id, values in readings.items():
            all_readings.setdefault(sensor_id, []).extend(values)
    return EslDataset({
        sensor_id: sorted(remove_esl_duplicates(readings), key=lambda r: r.start_time)
        for sensor_id, readings in all_readings.items()
    }, sources)
