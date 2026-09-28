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

def _get_text(element, xpath):
  node = element.find(xpath, NS)
  return node.text if node is not None else None

def _extract_sensor_id(document_id):
  return document_id.rsplit("_", 1)[-1]

def _parse_timestamp(value):
  return datetime.fromisoformat(value.replace("Z", "+00:00"))

def _parse_observations(root, start, resolution) -> List[Messwert]:
  messwerte = []
  observations = root.findall(".//rsm:Observation", NS)
  for obs in observations:
    sequence = int(_get_text(obs, ".//rsm:Position/rsm:Sequence"))
    volume = float(_get_text(obs, ".//rsm:Volume"))
    timestamp = start + timedelta(minutes=(sequence - 1) * resolution)
    messwerte.append(Messwert(timestamp, sequence, volume))
  return messwerte

def parse_sdat_file(file_path: Path) -> Dict[str, List[Messwert]]:
  root = ET.parse(file_path).getroot()
  document_id = _get_text(root, ".//rsm:InstanceDocument/rsm:DocumentID")
  sensor_id = _extract_sensor_id(document_id)

  if sensor_id not in ALLOWED_SENSOR_IDS:
    return {}

  start = _get_text(root, ".//rsm:Interval/rsm:StartDateTime")
  start = _parse_timestamp(start)

  resolution = int(_get_text(root, ".//rsm:Resolution/rsm:Resolution"))

  messwerte = _parse_observations(root, start, resolution)
  return {sensor_id: messwerte}