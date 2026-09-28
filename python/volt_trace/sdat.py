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
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

NS = {"rsm": "http://www.strom.ch"}
ALLOWED_SENSOR_IDS = {"ID735", "ID742"}


@dataclass
class Messwert:
    timestamp: datetime
    sequence: int
    volume: float


def _get_text(element, xpath) -> str | None:
    node = element.find(xpath, NS)
    if node is None or node.text is None:
        raise ValueError(f"Tag nicht gefunden: {xpath}")
    return node.text


def _extract_sensor_id(document_id) -> str:
    return document_id.rsplit("_", 1)[-1]


def _parse_timestamp(value) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def sort_messwerte_by_time(messwerte: List[Messwert]) -> List[Messwert]:
    messwerte.sort(key=lambda x: x.timestamp)
    return messwerte

def remove_duplicates(messwerte: List[Messwert]) -> List[Messwert]:
    unique_messwerte: List[Messwert] = []
    seen_timestamps = set()
    for messwert in messwerte:
        if messwert.timestamp not in seen_timestamps:
            unique_messwerte.append(messwert)
            seen_timestamps.add(messwert.timestamp)
    return unique_messwerte

def _parse_observations(root, start, resolution) -> List[Messwert]:
    messwerte = []
    observations = root.findall(".//rsm:Observation", NS)
    for obs in observations:
        sequence = int(_get_text(obs, ".//rsm:Position/rsm:Sequence"))
        volume = float(_get_text(obs, ".//rsm:Volume"))
        timestamp = start + timedelta(minutes=(sequence - 1) * resolution)
        messwerte.append(Messwert(timestamp, sequence, volume))
        
    messwerte = sort_messwerte_by_time(messwerte)
    messwerte = remove_duplicates(messwerte)
    return messwerte


def parse_sdat_file(file_path: Path) -> Dict[str, List[Messwert]]:
    """Liest ein sdat-File ein. Gibt {sensor_id: [Messwerte]} zurück,
    oder ein leeres Dict, wenn der Sensor nicht in ALLOWED_SENSOR_IDS ist."""
    root = ET.parse(file_path).getroot()
    document_id = _get_text(root, ".//rsm:InstanceDocument/rsm:DocumentID")
    sensor_id = _extract_sensor_id(document_id)

    if sensor_id not in ALLOWED_SENSOR_IDS:
        return {}

    start = _get_text(root, ".//rsm:Interval/rsm:StartDateTime")
    start = _parse_timestamp(start)

    resolution = int(_get_text(root, ".//rsm:Resolution/rsm:Resolution"))

    messwerte = _parse_observations(root, start, resolution)
    return sensor_id, messwerte