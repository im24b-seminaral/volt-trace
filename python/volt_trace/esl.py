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
TARIF_REGISTER = ("1", "2")
OBIS_GRUPPE_TO_SENSOR = {
    "1-1:1.8": "ID742",
    "1-1:2.8": "ID735",
}


def _obis_gruppe(obis: str) -> str | None:
    """OBIS-Basis ohne Tarifregister (.1 Hochtarif, .2 Niedertarif)."""
    prefix, register = obis.rsplit(".", 1)
    if register in TARIF_REGISTER:
        return prefix
    return None


def _effektiver_zaehlerstand_pro_gruppe(werte: Dict[str, float]) -> Dict[str, float]:
    """Summiert Hoch- und Niedertarif je OBIS-Gruppe, wenn beide Register vorhanden."""
    nach_gruppe: Dict[str, Dict[str, float]] = {}
    for obis, value in werte.items():
        gruppe = _obis_gruppe(obis)
        if gruppe is None:
            continue
        register = obis.rsplit(".", 1)[1]
        nach_gruppe.setdefault(gruppe, {})[register] = value

    summen: Dict[str, float] = {}
    for gruppe, register_werte in nach_gruppe.items():
        if all(r in register_werte for r in TARIF_REGISTER):
            summen[gruppe] = round(
                register_werte["1"] + register_werte["2"], 4
            )
    return summen


@dataclass
class Zaehlerstand:
    start_time: datetime   # Ablesezeitpunkt in UTC
    start_value: float     # absoluter Zählerstand in kWh (HT + NT)


def _get_attribute(element, name) -> str:
    value = element.get(name)
    if value is None:
        raise ValueError(f"Attribut nicht gefunden: {name}")
    return value


def _parse_start_time(value) -> datetime:
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
    result: Dict[str, List[Zaehlerstand]] = {
        sensor_id: [] for sensor_id in OBIS_GRUPPE_TO_SENSOR.values()
    }

    for time_period in root.iter("TimePeriod"):
        start_time = _parse_start_time(_get_attribute(time_period, "end"))
        werte = _parse_value_rows(time_period)
        summen = _effektiver_zaehlerstand_pro_gruppe(werte)

        for gruppe, start_value in summen.items():
            sensor_id = OBIS_GRUPPE_TO_SENSOR.get(gruppe)
            if sensor_id is not None:
                result[sensor_id].append(Zaehlerstand(start_time, start_value))

    return {sensor_id: werte for sensor_id, werte in result.items() if werte}
