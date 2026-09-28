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

ZEITZONE_ESL = ZoneInfo("Europe/Zurich")
OBIS_MAPPING = {
    "ID742": ("1-1:1.8.1", "1-1:1.8.2"),
    "ID735": ("1-1:2.8.1", "1-1:2.8.2"),
}


@dataclass
class Zaehlerstand:
    timestamp: datetime
    value: float


def _get_attribute(element, name) -> str:
    value = element.get(name)
    if value is None:
        raise ValueError(f"Attribut nicht gefunden: {name}")
    return value


def _parse_timestamp(value) -> datetime:
    lokal = datetime.fromisoformat(value).replace(tzinfo=ZEITZONE_ESL)
    return lokal.astimezone(timezone.utc)


def _parse_value_rows(time_period) -> Dict[str, float]:
    return {
        _get_attribute(row, "obis"): float(_get_attribute(row, "value"))
        for row in time_period.iter("ValueRow")
    }


def parse_esl_file(file_path: Path) -> Dict[str, List[Zaehlerstand]]:
    """Liest ein ESL-File ein. Gibt {sensor_id: [Zaehlerstaende]} zurück.
    Ein ESL-File enthält beide Sensoren, deshalb kommen bis zu zwei Einträge zurück."""
    root = ET.parse(file_path).getroot()
    result: Dict[str, List[Zaehlerstand]] = {sensor_id: [] for sensor_id in OBIS_MAPPING}

    for time_period in root.iter("TimePeriod"):
        timestamp = _parse_timestamp(_get_attribute(time_period, "end"))
        werte = _parse_value_rows(time_period)

        for sensor_id, (hochtarif, niedertarif) in OBIS_MAPPING.items():
            if hochtarif in werte and niedertarif in werte:
                value = round(werte[hochtarif] + werte[niedertarif], 4)
                result[sensor_id].append(Zaehlerstand(timestamp, value))

    return {sensor_id: werte for sensor_id, werte in result.items() if werte}

