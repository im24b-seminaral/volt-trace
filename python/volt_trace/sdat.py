"""
sdat.py - Einlesen und Parsen von SDAT-XML-Dateien.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from volt_trace.quantities import round_kwh

NS = {"rsm": "http://www.strom.ch"}
_POSITION = "{http://www.strom.ch}Position"
_SEQUENCE = "{http://www.strom.ch}Sequence"
_VOLUME = "{http://www.strom.ch}Volume"
_OBSERVATION = "{http://www.strom.ch}Observation"
SENSOR_DIRECTIONS = {"ID742": "consumption", "ID735": "feed-in"}


@dataclass
class MeasuredValue:
    """timestamp = Intervallende (UTC), volume = Verbrauch im Intervall (Beginn, Ende]."""
    timestamp: datetime
    sequence: int
    volume: float
    resolution_minutes: int = 15
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


def _get_text(element, xpath) -> str:
    node = element.find(xpath, NS)
    if node is None or node.text is None:
        raise ValueError(f"Tag not found: {xpath}")
    return node.text


def _find_text(element, xpath) -> str | None:
    node = element.find(xpath, NS)
    return node.text if node is not None and node.text is not None else None


def _extract_sensor_id(document_id) -> str:
    return document_id.rsplit("_", 1)[-1]


def _parse_timestamp(value) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_creation(root) -> datetime:
    creation = _find_text(root, ".//rsm:Creation") or _find_text(
        root, ".//rsm:InstanceDocument/rsm:Creation"
    )
    if creation is None:
        raise ValueError("Creation fehlt")
    return _parse_timestamp(creation)


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
    return int(sequence_text), round_kwh(float(volume_text))


def _validate_interval(
    start: datetime,
    end: datetime,
    resolution_minutes: int,
    measured_values: List[MeasuredValue],
) -> None:
    count = len(measured_values)
    if count == 0:
        raise ValueError("Keine Observations im Intervall")
    max_seq = max(mv.sequence for mv in measured_values)
    duration_minutes = int((end - start).total_seconds() // 60)
    if duration_minutes % resolution_minutes != 0:
        raise ValueError("Intervalllänge ist kein Vielfaches der Auflösung")
    expected = duration_minutes // resolution_minutes
    if count != max_seq or max_seq != expected:
        raise ValueError(
            f"Sequenz/Anzahl passt nicht zum Intervall "
            f"(count={count}, max_seq={max_seq}, erwartet={expected})"
        )
    sequences = {mv.sequence for mv in measured_values}
    if sequences != set(range(1, max_seq + 1)):
        raise ValueError("Unvollständige oder doppelte Sequenznummern")


def _parse_observations(root, start, end, resolution_minutes: int,
                        source: SdatSource | None = None) -> List[MeasuredValue]:
    step = timedelta(minutes=resolution_minutes)
    measured_values: List[MeasuredValue] = []
    in_order = resolution_minutes > 0
    previous_sequence = 0
    for obs in root.iter(_OBSERVATION):
        sequence, volume = _parse_observation(obs)
        if sequence <= previous_sequence:
            in_order = False
        previous_sequence = sequence
        measured_values.append(
            MeasuredValue(
                start + step * sequence,
                sequence,
                volume,
                resolution_minutes,
                source,
            )
        )

    _validate_interval(start, end, resolution_minutes, measured_values)

    if in_order:
        return measured_values
    measured_values = sort_measured_values_by_time(measured_values)
    return remove_duplicates(measured_values)


def _parse_resolution_minutes(root, start: datetime) -> int:
    resolution_text = _find_text(root, ".//rsm:Resolution/rsm:Resolution")
    if resolution_text is not None:
        unit = _find_text(root, ".//rsm:Resolution/rsm:Unit")
        if unit is not None and unit.strip().upper() != "MIN":
            raise ValueError(f"Unbekannte Auflösungseinheit: {unit} (nur MIN erlaubt)")
        minutes = int(resolution_text)
        if minutes <= 0:
            raise ValueError("Ungültige Auflösung")
        return minutes

    end_text = _find_text(root, ".//rsm:Interval/rsm:EndDateTime")
    anzahl = len(root.findall(".//rsm:Observation", NS))
    if end_text is None or anzahl == 0:
        raise ValueError("Startzeit, Ende oder Messwerte fehlen")
    end = _parse_timestamp(end_text)
    duration = end - start
    minutes = int(duration.total_seconds() // 60 // anzahl)
    if minutes <= 0:
        raise ValueError("Auflösung konnte nicht berechnet werden")
    return minutes


def parse_sdat_file(file_path: Path, source_path: str | None = None) -> Tuple[datetime, Dict[str, List[MeasuredValue]]]:
    root = ET.parse(file_path).getroot()
    creation = _parse_creation(root)
    document_id = _find_text(root, ".//rsm:DocumentID") or _get_text(
        root, ".//rsm:InstanceDocument/rsm:DocumentID"
    )
    sensor_id = _extract_sensor_id(document_id)

    start_text = _find_text(root, ".//rsm:Interval/rsm:StartDateTime")
    end_text = _find_text(root, ".//rsm:Interval/rsm:EndDateTime")
    if start_text is None or end_text is None:
        raise ValueError("Startzeit oder Intervallende fehlt")
    start = _parse_timestamp(start_text)
    end = _parse_timestamp(end_text)
    resolution_minutes = _parse_resolution_minutes(root, start)
    source = SdatSource(
        source_path or file_path.name,
        document_id,
        creation,
        start,
        end,
        resolution_minutes,
        _find_text(root, ".//rsm:Resolution/rsm:Unit"),
        _find_text(root, ".//rsm:InstanceDocument/rsm:Status"),
    )
    measured_values = _parse_observations(root, start, end, resolution_minutes, source)
    return creation, {sensor_id: measured_values}


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
                                "reason": "Keine Messwerte", "skippedRecords": 0})
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
                bereits_gelesen[messwert.timestamp] = messwert

    return SdatDataset({
        sensor_id: sorted(messwerte.values(), key=lambda m: m.timestamp)
        for sensor_id, messwerte in pro_sensor.items()
    }, sources)
