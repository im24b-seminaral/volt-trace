"""
test_analysis.py - Unit- und Integrationstests für das volt_trace Modul.

Zweck und Aufgaben dieser Datei:
--------------------------------
1. Tests für SDAT-Parsing (sdat.py):
   - Korrektes Auslesen von DocumentID (ID735, ID742).
   - Validierung von Start-/End-Zeitpunkten und Resolutions (z. B. 15 MIN).
   - Korrekte Extraktion von Observation-Sequenzen und Verbrauchsvolumen.
2. Tests für ESL-Parsing (esl.py):
   - Korrektes Parsen von TimePeriod end und OBIS-Kennzahlen.
   - Richtige Addition von Hochtarif- und Niedertarif-Werten:
     * 1-1:1.8.1 + 1-1:1.8.2 -> ID742 (Netzbezug)
     * 1-1:2.8.1 + 1-1:2.8.2 -> ID735 (Solar-Einspeisung)
3. Tests für Analyse und Berechnung (analysis.py):
   - Duplikaterkennung und -bereinigung anhand von Zeitstempeln (UTC).
   - Umrechnung relativer Verbrauchswerte in korrekte fortlaufende absolute Zählerstände.
   - Mathematische Konsistenz der aufsummierten Werte im Vergleich zu den ESL-Zählerständen.
4. Tests für Datenexport (export.py):
   - Überprüfung des CSV-Formats (Spaltenüberschriften: timestamp, value; Dateinamen: ID735.csv, ID742.csv).
   - Validierung der JSON-Exportstruktur (sensorId, ts, value).
"""
