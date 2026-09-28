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
import pandas
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

NS = {"rsm": "http://www.strom.ch"}

@dataclass
class Messwert:
    timestamp: datetime
    sequence: int
    volume: float

def _parse_observations(root, start, resolution) -> List[Messwert]:
  messwerte = []
  observations = root.findall(".//rsm:Observation", NS)
  for obs in observations:
    sequence = int(obs.find(".//rsm:Position/rsm:Sequence", NS).text)
    volume = float(obs.find(".//rsm:Volume", NS).text)
    timestamp = start + timedelta(minutes=(sequence - 1) * resolution)
    messwerte.append(Messwert(timestamp, sequence, volume))
  return messwerte

def parse_sdat_file(file_path: Path) -> Dict[str, List[Messwert]]:
  root = ET.parse(file_path).getroot()
  document_id = root.find(".//rsm:InstanceDocument/rsm:DocumentID", NS).text
  sensor_id = document_id.rsplit("_", 1)[-1]

  start = root.find(".//rsm:Interval/rsm:StartDateTime", NS).text
  start = datetime.fromisoformat(start.replace("Z", "+00:00"))

  resolution = int(root.find(".//rsm:Resolution/rsm:Resolution", NS).text)

  messwerte = _parse_observations(root, start, resolution)
  return {sensor_id: messwerte}

