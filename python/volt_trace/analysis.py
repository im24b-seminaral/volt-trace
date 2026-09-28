"""
analysis.py - Datenaggregation, Verknüpfung und Zählerstandsberechnung.

Zweck und Aufgaben dieser Datei:
--------------------------------
1. Datenmodell «Messwert»:
   - Speicherung von:
     * timestamp: Eindeutiger Zeitstempel in UTC (dient als Primärschlüssel / Key)
     * relative_value: Relativer Verbrauchswert aus sdat (z. B. in 15-Minuten-Intervallen)
     * absolute_value: Berechneter absoluter Zählerstand zu diesem Zeitpunkt
2. Duplikatbehandlung und Sortierung:
   - Zusammenführen von Messwerten in einer sortierten, duplikatfreien Datenstruktur
     (z. B. Dict sortiert nach Timestamp oder pandas.DataFrame mit Timestamp-Index).
3. Verrechnung von ESL- und SDAT-Daten:
   - Verbinden der relativen SDAT-Verbrauchswerte mit den absoluten ESL-Stichtagszählerständen:
     * ID735 (Einspeisung) & ID742 (Netzbezug).
   - Fortlaufende Aufsummierung der relativen Werte ausgehend vom Referenz-Zählerstand,
     um den exakten absoluten Zählerstand zu jedem Zeitstempel zu bestimmen.
4. Analyse- & Auswertungsfunktionen:
   - Vorbereitung aggregierter Daten für Verbrauchsdiagramme (Verbrauch pro Intervall / Tag).
   - Vorbereitung aggregierter Daten für Zählerstandsdiagramme (kontinuierlicher Verlauf).
"""

from typing import List, Dict
from datetime import datetime
from pathlib import Path

# pyrefly: ignore [missing-import]
from sdat import Messwert, load_sdat_folder

# pyrefly: ignore [missing-import]
from esl import Zaehlerstand, load_esl_folder

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

def berechne_zaehlerstand(
    messwerte: List[Messwert],  # sortierte, duplikatfreie Liste aus sdat.py
    start_value: float,  # absoluter Zählerstand aus dem ESL-File
    start_time: datetime,  # Zeitpunkt, zu dem start_value gilt (ESL TimePeriod)
) -> List[Zaehlerstand]:

    messwerte = [mw for mw in messwerte if mw.timestamp >= start_time]
    messwerte = sort_messwerte_by_time(messwerte)
    messwerte = remove_duplicates(messwerte)
    running_total = start_value
    results: List[Zaehlerstand] = []

    for mw in messwerte:
        running_total += mw.volume
        results.append(Zaehlerstand(mw.timestamp, running_total))
    return results


def calculate_all_meter_readings(
    sdat_daten: Dict[str, List[Messwert]],
    esl_daten: Dict[str, List[Zaehlerstand]],
) -> Dict[str, List[Zaehlerstand]]:
    ergebnis: Dict[str, List[Zaehlerstand]] = {}
    for sensor_id, messwerte in sdat_daten.items():
        esl_werte = esl_daten.get(sensor_id, [])
        if not esl_werte:
            continue

        anker = min(esl_werte, key=lambda z: z.start_time)
        ergebnis[sensor_id] = berechne_zaehlerstand(
            messwerte,
            start_value=anker.start_value,
            start_time=anker.start_time,
        )

    return ergebnis


if __name__ == "__main__":
    sdat = load_sdat_folder(Path("C:\\Users\\andri\\Downloads\\XML-Files\\SDAT-Files"))
    esl = load_esl_folder(Path("C:\\Users\\andri\\Downloads\\XML-Files\\ESL-Files"))

    zaehlerstaende = calculate_all_meter_readings(sdat, esl)
    for sensor_id, werte in zaehlerstaende.items():
        print(f"{sensor_id}: {len(werte)} Werte")
        print(f"  erster: {werte[0]}")
        print(f"  letzter: {werte[-1]}")
