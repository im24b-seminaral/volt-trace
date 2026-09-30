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
# Tags in Clark-Schreibweise: find() mit einem einfachen Tag ist viel schneller
# als ein XPath-Ausdruck mit Namespace-Präfix (wichtig bei ~1.3 Mio Observations).
_POSITION = "{http://www.strom.ch}Position"
_SEQUENCE = "{http://www.strom.ch}Sequence"
_VOLUME = "{http://www.strom.ch}Volume"
_OBSERVATION = "{http://www.strom.ch}Observation"
# Bekannte Sensoren; alle anderen werden eingelesen und als "other" geführt (FA-03).
SENSOR_DIRECTIONS = {"ID742": "consumption", "ID735": "feed-in"}
 
@dataclass
class MeasuredValue:
    timestamp: datetime
    sequence: int
    volume: float
    source: "SdatSource | None" = None


@dataclass(frozen=True)
class SdatSource:
    file: str
    document_id: str
    creation: datetime
    interval_start: datetime
    interval_end: datetime | None
    resolution_minutes: int
    resolution_unit: str | None
    document_status: str | None


class SdatDataset(dict[str, List[MeasuredValue]]):
    def __init__(self, values: Dict[str, List[MeasuredValue]], sources: List[SdatSource]):
        super().__init__(values)
        self.sources = sources
 
 
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
 
def _parse_observation(obs) -> Tuple[int, float]:
    """Sequence und Volume einer Observation.
 
    Schneller Weg: direkt über die Kind-Elemente. Findet er nichts, gilt der
    ursprüngliche XPath (gleiche Ergebnisse, gleiche Fehlermeldung)."""
    sequence_text = volume_text = None
    for child in obs:
        if child.tag == _POSITION:
            node = child.find(_SEQUENCE)
            if node is not None:
                sequence_text = node.text
        elif child.tag == _VOLUME:
            volume_text = child.text
    if sequence_text is None:
        sequence_text = _get_text(obs, ".//rsm:Position/rsm:Sequence")
    if volume_text is None:
        volume_text = _get_text(obs, ".//rsm:Volume")
    return int(sequence_text), float(volume_text)
 
 
def _parse_observations(root, start, resolution, source: SdatSource | None = None) -> List[MeasuredValue]:
    measured_values = []
    step = timedelta(minutes=resolution)
    in_order = resolution > 0   # Sequence streng aufsteigend -> schon sortiert und ohne Duplikate
    previous_sequence = 0
    for obs in root.iter(_OBSERVATION):
        sequence, volume = _parse_observation(obs)
        if sequence <= previous_sequence:
            in_order = False
        previous_sequence = sequence
        measured_values.append(MeasuredValue(start + step * (sequence - 1), sequence, volume, source))
 
    if in_order:
        return measured_values
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
 
def parse_sdat_file(file_path: Path, source_path: str | None = None) -> Tuple[datetime, Dict[str, List[MeasuredValue]]]:
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
 
    end_text = _find_text(root, ".//rsm:Interval/rsm:EndDateTime")
    source = SdatSource(
        source_path or file_path.name,
        document_id,
        creation,
        start,
        _parse_timestamp(end_text) if end_text else None,
        resolution,
        _find_text(root, ".//rsm:Resolution/rsm:Unit"),
        _find_text(root, ".//rsm:InstanceDocument/rsm:Status"),
    )
    return creation, {sensor_id: _parse_observations(root, start, resolution, source)}
 
def load_sdat_folder(folder_path: Path, skipped: List[dict] | None = None) -> Dict[str, List[MeasuredValue]]:
    eingelesen = []
    sources: List[SdatSource] = []
    for xml_file in sorted(path for path in folder_path.rglob("*")
                           if path.is_file() and path.suffix.lower() == ".xml"):
        source_path = xml_file.relative_to(folder_path).as_posix()
        try:
            creation, messwerte_pro_sensor = parse_sdat_file(xml_file, source_path)
        except (ET.ParseError, ValueError, OSError) as error:
            if skipped is not None:
                reason = ("Kein gültiges XML" if isinstance(error, ET.ParseError)
                          else f"Fehlerhafte Daten: {error}")
                skipped.append({"file": source_path, "kind": "file", "reason": reason, "skippedRecords": 0})
            continue
        if not messwerte_pro_sensor or not any(messwerte_pro_sensor.values()):
            if skipped is not None:
                skipped.append({"file": source_path, "kind": "file",
                                "reason": "Startzeit oder Messwerte fehlen", "skippedRecords": 0})
            continue
        source = next(iter(messwerte_pro_sensor.values()))[0].source
        if source is not None:
            sources.append(source)
        eingelesen.append((creation, source_path, messwerte_pro_sensor))
    eingelesen.sort(key=lambda eintrag: (eintrag[0], eintrag[1]))
 
    pro_sensor: Dict[str, Dict[datetime, MeasuredValue]] = {}
    for _creation, _dateiname, messwerte_pro_sensor in eingelesen:
        for sensor_id, messwerte in messwerte_pro_sensor.items():
            bereits_gelesen = pro_sensor.setdefault(sensor_id, {})
            for messwert in messwerte:
                bereits_gelesen[messwert.timestamp] = messwert   # last wins
 
    return SdatDataset({
        sensor_id: sorted(messwerte.values(), key=lambda m: m.timestamp)
        for sensor_id, messwerte in pro_sensor.items()
    }, sources)
