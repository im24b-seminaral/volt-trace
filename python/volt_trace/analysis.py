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

from typing import List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from volt_trace.sdat import Messwert

@dataclass
class Zaehlerstand:
    timestamp: datetime
    value: float


def berechne_zaehlerstand(
    messwerte: List[Messwert],   # sortierte, duplikatfreie Liste aus sdat.py
    start_value: float,          # absoluter Zählerstand aus dem ESL-File
    start_time: datetime,        # Zeitpunkt, zu dem start_value gilt (ESL TimePeriod)
    ) -> List[Zaehlerstand]:
    
    messwerte = [mw for mw in messwerte if mw.timestamp >= start_time]
    
    running_total = start_value
    results: List[Zaehlerstand] = []

    for mw in messwerte:
        running_total += mw.volume
        results.append(Zaehlerstand(mw.timestamp, running_total))
    return results

