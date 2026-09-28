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
