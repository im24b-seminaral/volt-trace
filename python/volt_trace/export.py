"""
export.py - Export von Zähler- und Verbrauchsdaten (CSV, JSON, HTTP-POST).

Zweck und Aufgaben dieser Datei:
--------------------------------
1. CSV-Export (Pflicht):
   - Exportiert die berechneten Daten als CSV-Datei.
   - Dateiname entspricht der SensorID (z. B. `ID735.csv`, `ID742.csv`).
   - Format:
       timestamp, value
       1503495303, 1129336.0
       1503496303, 1129339.0
     * Zeitstempel als Unix-Timestamp in UTC.
     * value als absoluter Zählerstand im kleinstmöglichen verfügbaren Zeitabstand.
2. JSON-Export (Nice to have):
   - Strukturierung und Speicherung der Daten im geforderten JSON-Format:
     [
       {
         "sensorId": "ID742",
         "data": [
           { "ts": "1503495302", "value": 82.03 }, ...
         ]
       },
       {
         "sensorId": "ID735",
         "data": [
           { "ts": "1503495303", "value": 1129336.0 }, ...
         ]
       }
     ]
3. HTTP-POST-Upload (Nice to have):
   - Funktion zum Senden der JSON-formatierten Daten per HTTP POST Request an einen Server/API.
"""
