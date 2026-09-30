# Offene Punkte – Volt Trace

Was laut Pflichtenheft v0.9 (Gruppe 3, Energieagentur Bünzli) noch fehlt oder fehlerhaft ist. Die Projektdokumentation steht im [README.md](README.md).

Stand: 30.09.2026, nach Commit `120bc71`. Referenzen (FA/NFA) beziehen sich auf das Pflichtenheft.

## 1. Fachlogik Python (Muss, höchste Priorität)

- [ ] **FA-05: Zeitstempel falsch.** [sdat.py](python/volt_trace/sdat.py) rechnet `start + (sequence - 1) * resolution`, beschriftet also mit dem Intervall*beginn*. Gefordert ist das Intervall*ende*: `start + sequence * resolution`. Alle Werte liegen aktuell 15 min zu früh.
- [ ] **FA-05:** Einheit von `rsm:Resolution` (`rsm:Unit`) prüfen statt immer Minuten anzunehmen. `rsm:Interval/EndDateTime` einlesen und prüfen: Anzahl Werte = (Ende − Beginn) / Auflösung.
- [ ] **FA-06: Duplikatregel verkehrt.** Dateien werden in `glob`-Reihenfolge gelesen und `remove_duplicates` behält den *ersten* Wert. Gefordert: Dateien nach `rsm:Creation` aufsteigend (bei Gleichstand nach Dateiname) einlesen, der *zuletzt* gelesene Wert gewinnt. Ohne Korrektur enthält die Kurve rund 18 % falsche Nullwerte.
- [ ] **FA-07: Umrechnung unvollständig.** [analysis.py](python/volt_trace/analysis.py) summiert nur ab dem ersten ESL-Anker auf. Es fehlen:
  - Neuansatz an jedem ESL-Ablesezeitpunkt
  - Gewichtungsfaktor je Intervall (ESL-Differenz / Summe sdat)
  - Ausweisung von Faktor, ungewichteter Summe und ESL-Differenz je Intervall (Ansatz in `compare_esl_vs_sdat.py` wiederverwenden)
  - Rückwärtsrechnung vor dem ersten Anker (Werte davor werden aktuell verworfen)
  - Randfälle: nach dem letzten Anker, Summe = 0
- [ ] **FA-03:** `ALLOWED_SENSOR_IDS` in [sdat.py](python/volt_trace/sdat.py) entfernen. Alle Sensoren (auch ID26256, ID26257, ID26263) einlesen, Zählerstand nur wo ein ESL-Anker existiert.
- [ ] **FA-01:** `rsm:Creation` einlesen (wird für FA-06 gebraucht). Unterordner rekursiv lesen (`rglob`). Anzahl gefundener, eingelesener und übersprungener Dateien ausweisen, inkl. Fehler beim Parsen.
- [ ] **FA-02:** ESL `Meter factoryNo` und `Status` einlesen. Zeilen mit Status ≠ V überspringen und ausweisen.
- [ ] **NFA-06:** `load_sdat_folder` / `load_esl_folder` ohne try/except, eine defekte Datei bricht den ganzen Lauf ab. Die 32 sdat-Files ohne Resolution müssen gemeldet, aber nicht zum Absturz führen (sonst fehlt ID26263).
- [ ] **NFA-04:** Aufsummieren in `float` erzeugt Rundungsfehler. Zahlentyp und Rundung festlegen (z. B. `Decimal` oder Rundung auf 4 Stellen) und dokumentieren.
- [ ] **NFA-05:** Tageswerte in [cli.py](python/volt_trace/cli.py) (`_aggregate_by_day`) werden mit `datetime.combine` ohne Zeitzone erzeugt. Mit `tzinfo=timezone.utc` erzeugen.

## 2. Performance und Architektur

- [ ] **NFA-03: erstes Einlesen zu langsam.** Seit Commit `789a619` speichert `cli.py` das Ergebnis pro Datensatz in `.processed-v1.cache`, weitere Anzeigen sind dadurch schnell. Das erste Einlesen aller sdat-Files dauert aber weiterhin ca. 70 s (Vorgabe: Lesen ≤ 10 s, Gesamtablauf < 60 s). Parser in `sdat.py` beschleunigen und Zeit am vollständigen Datensatz messen.
- [ ] **NFA-03:** Fortschrittsanzeige beim Upload/Einlesen (aktuell nur „Lade hoch …“).
- [ ] **NFA-01 / NFA-11: Abweichung vom Pflichtenheft.** Das Pflichtenheft verlangt eine HTTP-API mit FastAPI/uvicorn; umgesetzt ist ein direkter Aufruf der Python-CLI aus Next.js. Entweder FastAPI umsetzen oder das Pflichtenheft (NFA-01, NFA-11, Kap. 5.3) für Version 1.0 anpassen.
- [ ] **NFA-01:** Python-Teil ist kaum objektorientiert (Funktionen + Dataclasses). Klassen für Einlesen, Datenmodell, Berechnung, Export einführen.
- [ ] **NFA-02:** Ein gemeinsames Datenmodell für Messwerte (Zeitpunkt, relativer Wert, absoluter Zählerstand). Aktuell gibt es `MeasuredValue`, `EslMeterReading` (wird auch für berechnete Zählerstände missbraucht) und `DataPoint` in `export.py`.
- [ ] **NFA-09:** `sort_measured_values_by_time` / `remove_duplicates` existieren dreimal (sdat, analysis, compare). Duplikatregel darf nur einmal im Code stehen.
- [ ] **NFA-09 / FA-10:** `cmd_export` in [cli.py](python/volt_trace/cli.py) baut das CSV selbst (ohne Rundung auf 4 Stellen), statt `to_csv_string` aus `export.py` zu verwenden. Anpassen auf:
  ```python
  from volt_trace.export import DataPoint, to_csv_string

  def cmd_export(dataset_dir: str, sensor_id: str):
      _sdat_data, _esl_data, meter_readings = _load(dataset_dir)
      points = [DataPoint(r.start_time, r.start_value) for r in meter_readings.get(sensor_id, [])]
      sys.stdout.write(to_csv_string(points))
  ```
  Danach wird `import csv` in `cli.py` nicht mehr gebraucht.

## 3. Frontend

- [ ] **FA-08 / FA-09:** Bezug und Einspeisung als **getrennte Reihen im selben Diagramm** darstellen (aktuell nur ein Sensor).
- [ ] **FA-08 / FA-09:** Seit Commit `789a619` steht „Verbrauch (kWh) · UTC“ bzw. „Zählerstand (kWh) · UTC“ über dem Diagramm (`EnergyChart`). Titel direkt an den Achsen („Zeit (UTC)“, „kWh“) fehlen noch; prüfen, ob das für die Abnahme reicht.
- [ ] **FA-13:** JSON-Download über die Oberfläche anbieten. `to_json_string(data)` liefert den Inhalt (siehe „Export-Schnittstelle“); in `cli.py` fehlt dafür noch ein Kommando, z. B. `export-json`.

## 4. Sicherheit und Datenschutz

- [ ] **NFA-12:** Hochgeladene Daten bleiben dauerhaft in `nextjs/data/` liegen, seit `789a619` zusätzlich als `.processed-v1.cache` pro Datensatz. Beides muss beim Ende der Sitzung (bzw. nach Ablauf) gelöscht werden.
- [ ] **NFA-11 / NFA-12:** `next dev` ist aus dem Netzwerk erreichbar. Nur lokal binden: `next dev -H 127.0.0.1` (Script in `package.json` anpassen).
- [ ] `python/data/` enthält eine echte ESL-Datei im Repository. Entfernen bzw. nach `tests/fixtures/` verschieben, falls sie für Tests gebraucht wird.

## 5. Tests (Kap. 5.5)

- [ ] [test_esl.py](python/tests/test_esl.py) importiert alte Funktionsnamen (`_effektiver_zaehlerstand_pro_gruppe`, `_obis_gruppe`), pytest bricht beim Sammeln ab. Auf `_total_readings_by_obis_group` / `_obis_group` umstellen.
- [ ] [test_analysis.py](python/tests/test_analysis.py) enthält nur einen Docstring, keine Tests.
- [ ] Prüfdatensatz mit bekannten Werten für FA-07 / NFA-04 anlegen (vorwärts und rückwärts vom Anker).
- [ ] Tests für FA-05: Tagesdatei 96 Werte, Zeitumstellungstage 92 und 100 Werte, Monatsdatei 2'976 Werte.
- [ ] Tests für FA-06 (neueste Datei gewinnt) und FA-10 (CSV-Format).

## 6. Nachweise für die Abnahme

- [ ] **NFA-03:** Zeit am vollständigen Beispieldatensatz messen: Ordnerwahl bis Diagramm < 60 s, davon Übertragung ≤ 45 s und Lesen ≤ 10 s. Oberfläche darf nie länger als 1 s blockieren.
- [ ] **NFA-07:** Ordnerauswahl, Diagrammwechsel, Sensorauswahl, Zeitraumauswahl und Export in Chrome, Safari und Firefox testen.
- [ ] **NFA-08:** Vollständiger Durchlauf (Ordnerauswahl, Einlesen, beide Diagramme, CSV-Export) unter Windows und macOS, je in zwei Browsern.
- [ ] **NFA-13:** Speicherbedarf der Datenverarbeitung < 1 GB, Durchlauf auf einem Notebook mit 8 GB RAM ohne Auslagern. Falls die Übertragung zu langsam ist: Upload als ZIP-Archiv.
- [ ] **NFA-06:** Nachweis mit defekten/leeren Dateien: Meldung statt Abbruch, Oberfläche bleibt bedienbar.

## 7. Offene Fragen an den Auftraggeber (Kapitel 9, Meeting 30.09.2026)

Nach dem Meeting Antworten hier eintragen und betroffene Punkte oben anpassen.

- [ ] **F3:** Duplikatregel „neuestes `rsm:Creation` gewinnt“ korrekt? → betrifft FA-06
- [ ] **F4:** Ziel-URL und erwartete Antwort für HTTP POST? → betrifft FA-12
- [ ] **F8:** Gewichtung der Verbrauchswerte zwischen zwei Ablesungen gewünscht oder Werte unverändert? → betrifft FA-07, NFA-04
- [ ] **F12:** Öffentliche Bereitstellung auf einer Domain erlaubt? → betrifft FA-14
- [ ] **F13:** Anzeige in UTC oder Lokalzeit (Europe/Zurich)? → betrifft NFA-05, beide Diagramme, Zeitraumauswahl

## 8. Liefergegenstände ausserhalb des Codes (Kapitel 7)

- [ ] **L1:** Zwischenbericht als PDF + Meeting, Mi 30.09.2026, 09:00
- [ ] Pflichtenheft Version 1.0 nach Klärung der Fragen, zur Unterschrift (Kapitel 10)
- [ ] **L3:** Präsentation inklusive Demo, Fr 02.10.2026, 08:45
- [ ] **L4:** Dokumentation über alle IPERKA-Phasen, Fr 02.10.2026, 12:00. Muss u. a. enthalten: verwendete Rundung und Zahlentypen (NFA-04), Testprotokoll mit Soll-Ist-Vergleich je ESL-Intervall (Kap. 5.5).

## 9. Aufräumen

- [ ] **[main.py](python/volt_trace/main.py) passt nicht mehr zu `export.py`.** Es übergibt Tupel `(zeit, wert)` statt `DataPoint`-Objekten und ruft `export_json` mit einem Ordner statt einer Datei auf; der Export stürzt dadurch ab (siehe „Export-Schnittstelle“). Anpassen:
  1. Import ersetzen:
     ```python
     from volt_trace.export import DataPoint, export_csv, export_json
     ```
  2. Am Ende von `main()` die Tupel durch `DataPoint` ersetzen und die Export-Funktionen aufrufen:
     ```python
     readings = run_pipeline(args.esl_dir, args.sdat_dir)
     data = {
         sensor_id: [DataPoint(r.start_time, r.start_value) for r in values]
         for sensor_id, values in readings.items()
     }
     for file in export_csv(data, args.output_dir):
         print(f"CSV:  {file}")
     print(f"JSON: {export_json(data, args.output_dir / 'meter_readings.json')}")
     ```
     Wichtig: `export_json` erwartet einen **Dateipfad**, nicht den Ordner.
  3. Aufruf aus dem Ordner `python`:
     ```powershell
     python -m volt_trace.main --sdat-dir ..\XML-Files\SDAT-Files --esl-dir ..\XML-Files\ESL-Files --output-dir export
     ```
  4. Danach müssen im Ordner `export` die Dateien `ID742.csv`, `ID735.csv` und `meter_readings.json` liegen.
- [ ] Fest eingetragene Pfade (`C:\volt-trace\...`) in `analysis.py` und `compare_esl_vs_sdat.py` entfernen (NFA-08). `compare_esl_vs_sdat.py` importiert `from sdat import …` und funktioniert als Modul nicht.
- [ ] **NFA-01, Versionen:** `pyproject.toml` auf `requires-python = ">=3.14"` setzen, `pandas` und `openpyxl` entfernen (unbenutzt, nicht erlaubt). `requirements.txt` mit exakten Versionen. In `package.json` `engines.node` auf 24 setzen und `^`-Versionen fixieren; das Paket `cn` prüfen/entfernen.
- [ ] **Kap. 5.3:** Frontend-Abhängigkeiten (Radix, Lucide, Tailwind, shadcn …) im Pflichtenheft ergänzen, da die Liste als abschliessend gilt.
- [ ] Beispieldatensatz lokal: 45 ESL-Files / 44 Stichtage statt 47 / 45 laut Pflichtenheft. Datensatz oder Zahlen im Pflichtenheft prüfen.

## 10. Fehlende Liefergegenstände im Code

- [ ] **FA-11:** Klassendiagramm des Python-Teils inkl. Klassen für FA-12/FA-13, plus Komponentendiagramm (Muss).
- [ ] **FA-12 (Nice to have):** HTTP POST an einstellbare URL, Antwortstatus anzeigen. Vorschlag: Funktion `send_json(data, url) -> int` in `export.py`, die `to_json_payload(data)` als Body sendet und den Statuscode zurückgibt; `requests` erst dann in `requirements.txt` aufnehmen.
- [ ] **FA-14 (Nice to have):** öffentliche Bereitstellung, nur nach Zustimmung (F12).

## Erledigt

- [x] **export.py:** Dataclass `DataPoint` plus Funktionen im Stil von `sdat.py`/`esl.py`; `to_csv_string` / `to_json_payload` / `to_json_string` ohne Dateizugriff; CSV mit 4 Nachkommastellen; JSON-`ts` als Unix-Epoch-String in UTC gemäss Vorgabe des Auftraggebers; Fehler bei Zeitstempel ohne Zeitzone; Prüfung der Sensorkennung.
- [x] **NFA-03 / FA-08:** 15-Minuten-Auflösung nur noch mit Zeitraum von höchstens 31 Tagen (Commit `789a619`).
- [x] **NFA-03:** Zwischenspeicher pro Datensatz, damit nicht jede Anzeige alle Dateien neu einliest (Commit `789a619`, Test `test_cli_cache.py`).
- [x] Next.js: `params` als Promise, `maxBuffer` für grosse Exporte, Prüfung von Datensatz-ID und Sensorkennung, Zeitraumfilter mit UTC-Zeitzone (Commit `02cac85`).
