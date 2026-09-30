"""
sdat.py - Einlesen und Parsen von SDAT-XML-Dateien.

Zweck und Aufgaben dieser Datei:
--------------------------------
1. Einlesen von sdat-XML-Dateien (Schweizer Standard-Austauschformat für Zählerdaten).
2. Extrahieren der relevanten XML-Knoten:
   - <rsm:DocumentID>: Eindeutige Identifikation des Zählers / Sensors
     * ID735: Solaranlage Einspeisung (Strom ins Netz)
     * ID742: Netzbezug (Strom vom Netz ins Gebäude)
   - <rsm:Interval>: Start- und Endzeitpunkt des Messintervalls (in UTC)
     * <rsm:StartDateTime>, <rsm:EndDateTime>
   - <rsm:Resolution>: Zeitlicher Abstand / Intervall der Messwerte (z. B. 15 MIN)
   - <rsm:Observation>: Liste aller Messwerte im Intervall:
     * <rsm:Position> / <rsm:Sequence>: Fortlaufende Sequenznummer
     * <rsm:Volume>: Gemessener relativer Verbrauchswert / Menge im Intervall
     * <rsm:Condition>: Status-/Bedingungscode
3. Bereitstellung von Datenklassen / Datenstrukturen für relative Messwerte:
   - Erzeugung von Zeitstempeln (UTC) für jeden Sequence-Schritt basierend auf StartDateTime und Resolution.
   - Bereinigung von Duplikaten (z. B. identische Zeitstempel).
   - Rückgabe strukturierter Messreihen zur Weiterverarbeitung in analysis.py.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

NS = {"rsm": "http://www.strom.ch"}
ALLOWED_SENSOR_IDS = {"ID735", "ID742"}


@dataclass
class MeasuredValue:
    timestamp: datetime
    sequence: int
    volume: float


def _get_text(element, xpath) -> str | None:
    node = element.find(xpath, NS)
    if node is None or node.text is None:
        raise ValueError(f"Tag not found: {xpath}")
    return node.text


def _extract_sensor_id(document_id) -> str:
    return document_id.rsplit("_", 1)[-1]


def _parse_timestamp(value) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def _parse_creation(root) -> datetime:
    """Zeitpunkt, an dem das File erstellt wurde (rsm:Creation)."""
    return _parse_timestamp(_get_text(root, ".//rsm:InstanceDocument/rsm:Creation"))

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

def _parse_observations(root, start, resolution) -> List[MeasuredValue]:
    measured_values = []
    observations = root.findall(".//rsm:Observation", NS)
    for obs in observations:
        sequence = int(_get_text(obs, ".//rsm:Position/rsm:Sequence"))
        volume = float(_get_text(obs, ".//rsm:Volume"))
        timestamp = start + timedelta(minutes=(sequence - 1) * resolution)
        measured_values.append(MeasuredValue(timestamp, sequence, volume))
        
    measured_values = sort_measured_values_by_time(measured_values)
    measured_values = remove_duplicates(measured_values)
    return measured_values


def parse_sdat_file(file_path: Path) -> Dict[str, List[MeasuredValue]]:
    """Liest ein sdat-File ein. Gibt {sensor_id: [Messwerte]} zurück,
    oder ein leeres Dict, wenn der Sensor nicht in ALLOWED_SENSOR_IDS ist."""
    root = ET.parse(file_path).getroot()
    creation = _parse_creation(root)
    document_id = _get_text(root, ".//rsm:InstanceDocument/rsm:DocumentID")
    sensor_id = _extract_sensor_id(document_id)

    if sensor_id not in ALLOWED_SENSOR_IDS:
        return creation, {}

    start = _get_text(root, ".//rsm:Interval/rsm:StartDateTime")
    start = _parse_timestamp(start)

    resolution = int(_get_text(root, ".//rsm:Resolution/rsm:Resolution"))

    messwerte = _parse_observations(root, start, resolution)
    return creation, {sensor_id: messwerte}

def load_sdat_folder(folder_path: Path) -> Dict[str, List[MeasuredValue]]:
    """Liest alle Files eines Ordners, aufsteigend sortiert nach (Creation, Dateiname).
    Bei gleichem Zeitstempel gewinnt der zuletzt gelesene Wert (FA-06)."""
    eingelesen = []
    for xml_file in folder_path.glob("*.xml"):
        creation, messwerte_pro_sensor = parse_sdat_file(xml_file)
        eingelesen.append((creation, xml_file.name, messwerte_pro_sensor))
    eingelesen.sort(key=lambda eintrag: (eintrag[0], eintrag[1]))

    pro_sensor: Dict[str, Dict[datetime, MeasuredValue]] = {}
    for _creation, _dateiname, messwerte_pro_sensor in eingelesen:
        for sensor_id, messwerte in messwerte_pro_sensor.items():
            bereits_gelesen = pro_sensor.setdefault(sensor_id, {})
            for messwert in messwerte:
                bereits_gelesen[messwert.timestamp] = messwert   # last wins

    return {
        sensor_id: sorted(messwerte.values(), key=lambda m: m.timestamp)
        for sensor_id, messwerte in pro_sensor.items()
    }
