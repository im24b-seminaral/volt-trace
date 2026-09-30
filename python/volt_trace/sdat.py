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
# Bekannte Sensoren; alle anderen werden eingelesen und als "other" geführt (FA-03).
SENSOR_DIRECTIONS = {"ID742": "consumption", "ID735": "feed-in"}

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

def _find_text(element, xpath) -> str | None:
    """Wie _get_text, gibt aber None zurück statt eine Exception zu werfen."""
    node = element.find(xpath, NS)
    return node.text if node is not None and node.text is not None else None

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
        timestamp = start + timedelta(minutes=sequence * resolution)   # Intervallende (FA-05)
        measured_values.append(MeasuredValue(timestamp, sequence, volume))
        
    measured_values = sort_measured_values_by_time(measured_values)
    measured_values = remove_duplicates(measured_values)
    return measured_values

def _parse_resolution(root, start) -> int | None:
    """Messintervall in Minuten.

    Neuere Files (Schema 1p5) haben kein rsm:Resolution, sondern nur einen
    Wert für den ganzen Zeitraum. Dort ergibt sich die Auflösung aus der
    Intervall-Länge geteilt durch die Anzahl Messwerte.
    """
    resolution_text = _find_text(root, ".//rsm:Resolution/rsm:Resolution")
    if resolution_text is not None:
        return int(resolution_text)

    end_text = _find_text(root, ".//rsm:Interval/rsm:EndDateTime")
    anzahl = len(root.findall(".//rsm:Observation", NS))
    if end_text is None or anzahl == 0:
        return None
    duration = _parse_timestamp(end_text) - start
    return int(duration.total_seconds() // 60 // anzahl)

def parse_sdat_file(file_path: Path) -> Tuple[datetime, Dict[str, List[MeasuredValue]]]:
    """Liest ein sdat-File ein. Gibt (Creation-Zeitpunkt, {sensor_id: [Messwerte]})
    zurück. Alle Sensoren werden eingelesen (FA-03); das Dict ist leer, wenn dem
    File Pflichtangaben fehlen (NFA-06)."""
    root = ET.parse(file_path).getroot()
    creation = _parse_creation(root)
    document_id = _get_text(root, ".//rsm:InstanceDocument/rsm:DocumentID")
    sensor_id = _extract_sensor_id(document_id)

    start_text = _find_text(root, ".//rsm:Interval/rsm:StartDateTime")
    if start_text is None:
        return creation, {}   # unvollständiges File, wird übersprungen
    start = _parse_timestamp(start_text)

    resolution = _parse_resolution(root, start)
    if resolution is None:
        return creation, {}

    return creation, {sensor_id: _parse_observations(root, start, resolution)}

def load_sdat_folder(folder_path: Path, skipped: List[dict] | None = None) -> Dict[str, List[MeasuredValue]]:
    eingelesen = []
    for xml_file in sorted(folder_path.glob("*.xml")):
        try:
            creation, messwerte_pro_sensor = parse_sdat_file(xml_file)
        except (ET.ParseError, ValueError, OSError) as error:
            if skipped is not None:
                reason = ("Kein gültiges XML" if isinstance(error, ET.ParseError)
                          else f"Fehlerhafte Daten: {error}")
                skipped.append({"file": xml_file.name, "reason": reason, "skippedRecords": 0})
            continue
        if not messwerte_pro_sensor:
            if skipped is not None:
                skipped.append({"file": xml_file.name,
                                "reason": "Startzeit oder Messwerte fehlen", "skippedRecords": 0})
            continue
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