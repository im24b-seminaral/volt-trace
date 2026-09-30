# Offene Punkte – Volt Trace

Was laut Pflichtenheft v0.9 (Gruppe 3, Energieagentur Bünzli) noch fehlt oder fehlerhaft ist. Die Projektdokumentation steht im [README.md](README.md), die Python-Doku in [PYTHON.md](PYTHON.md).

Stand: 30.09.2026, nach Commit `3e3d24f` plus Umbau NFA-02 (Variante B, noch nicht committet). Referenzen (FA/NFA) beziehen sich auf das Pflichtenheft.

## 1. Fachlogik Python (Muss, höchste Priorität)

- [ ] **sdat-Werte passen nicht zu ESL (Faktor 3).** Zwischen zwei ESL-Stichtagen ist die Summe der sdat-Volumen bei ID742 und ID735 in jedem Intervall genau 3,00-mal so gross wie die ESL-Differenz (z. B. 31.12.18–28.02.19: ESL 4252.5 kWh, sdat 12757.8 kWh). Parser und Deduplizierung sind geprüft und nicht die Ursache. Folge: berechnete Zählerstände laufen von den ESL-Werten weg, rückwärts werden sie negativ, und `test_meter_readings_match_esl_within_tolerance` schlägt fehl (62 Abweichungen). Mit dem Auftraggeber klären (siehe F14), nicht ohne Begründung im Code korrigieren.
- [ ] **FA-05: Zeitstempel falsch.** [sdat.py](python/volt_trace/sdat.py) rechnet `start + (sequence - 1) * resolution`, beschriftet also mit dem Intervall*beginn*. Gefordert ist das Intervall*ende*: `start + sequence * resolution`. Alle Werte liegen aktuell 15 min zu früh. Bei der Umstellung die Konvention in `analysis.calculate_meter_readings` und `cli._aggregate_by_day` mit anpassen (siehe Kommentare dort).
- [ ] **FA-05:** Einheit von `rsm:Resolution` (`rsm:Unit`) prüfen statt immer Minuten anzunehmen. Prüfen: Anzahl Werte = (Ende − Beginn) / Auflösung (`rsm:EndDateTime` wird bisher nur für Files ohne Resolution gelesen).
- [ ] **FA-07: Umrechnung noch nicht vollständig.** Vorwärts- und Rückwärtsrechnung ab dem ersten ESL-Stichtag im sdat-Zeitraum ist umgesetzt. Es fehlen noch (abhängig von F8):
  - Neuansatz an jedem ESL-Ablesezeitpunkt
  - Gewichtungsfaktor je Intervall (ESL-Differenz / Summe sdat)
  - Ausweisung von Faktor, ungewichteter Summe und ESL-Differenz je Intervall (Ansatz in `compare_esl_vs_sdat.py`)
  - Randfälle: nach dem letzten Anker, Summe = 0
- [ ] **FA-01:** Unterordner rekursiv lesen. `cmd_sort_files` in [cli.py](python/volt_trace/cli.py) und die Loader verwenden nur `glob("*")` bzw. `glob("*.xml")`.
- [ ] **NFA-04:** Aufsummieren in `float` erzeugt Rundungsfehler. Zahlentyp und Rundung festlegen (z. B. `Decimal` oder Rundung auf 4 Stellen) und dokumentieren.

## 2. Performance und Architektur

- [ ] **NFA-03: erstes Einlesen zu langsam.** Seit Commit `789a619` speichert `cli.py` das Ergebnis pro Datensatz in `.processed-v1.cache`, weitere Anzeigen sind dadurch schnell. Das erste Einlesen aller sdat-Files dauert aber weiterhin ca. 70 s (Vorgabe: Lesen ≤ 10 s, Gesamtablauf < 60 s). Parser in `sdat.py` beschleunigen und Zeit am vollständigen Datensatz messen.
- [ ] **NFA-03:** Fortschrittsanzeige beim Upload/Einlesen (aktuell nur „Lade hoch …“).
- [ ] **NFA-01 / NFA-11: Abweichung vom Pflichtenheft.** Das Pflichtenheft verlangt eine HTTP-API mit FastAPI/uvicorn; umgesetzt ist ein direkter Aufruf der Python-CLI aus Next.js. Entweder FastAPI umsetzen oder das Pflichtenheft (NFA-01, NFA-11, Kap. 5.3) für Version 1.0 anpassen. Die FastAPI-Pakete sind aktuell nicht mehr in `requirements.txt`.
- [ ] **NFA-01:** Python-Teil ist kaum objektorientiert (Funktionen + Dataclasses). Klassen für Einlesen, Datenmodell, Berechnung, Export einführen.
- [ ] **NFA-02, Dokumentation:** Das Datenmodell ist umgesetzt (Variante B, siehe „Erledigt“). Offen: NFA-02 im Pflichtenheft umschreiben (`dict[datetime, MeterReading]` statt pandas-DataFrame) und im Projektbericht den Entscheid samt Begründung gegenüber der Vorgabe `TreeMap<Instant, Messwert>` festhalten.
- [ ] **NFA-09 / FA-10:** `cmd_export` in [cli.py](python/volt_trace/cli.py) baut das CSV selbst (ohne Rundung auf 4 Stellen), statt `to_csv_string` aus `export.py` zu verwenden. Anpassen auf:
  ```python
  from volt_trace.export import DataPoint, to_csv_string

  def cmd_export(dataset_dir: str, sensor_id: str):
      _sdat_data, _esl_data, meter_readings, _skipped = _load(dataset_dir)
      series = meter_readings.get(sensor_id, {})
      points = [DataPoint(r.timestamp, r.meter_value) for r in series.values()]
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

## 5. Tests (Kap. 5.5)

- [ ] Tests für FA-05: Tagesdatei 96 Werte, Zeitumstellungstage 92 und 100 Werte, Monatsdatei 2'976 Werte (die Tagesaggregation in `test_daily_aggregation.py` prüft 92/100 bereits, das Einlesen der sdat-Files noch nicht).
- [ ] Tests für FA-06 (neueste Datei gewinnt) und FA-10 (CSV-Format).

## 6. Nachweise für die Abnahme

- [ ] **NFA-03:** Zeit am vollständigen Beispieldatensatz messen: Ordnerwahl bis Diagramm < 60 s, davon Übertragung ≤ 45 s und Lesen ≤ 10 s. Oberfläche darf nie länger als 1 s blockieren.
- [ ] **NFA-07:** Ordnerauswahl, Diagrammwechsel, Sensorauswahl, Zeitraumauswahl und Export in Chrome, Safari und Firefox testen.
- [ ] **NFA-08:** Vollständiger Durchlauf (Ordnerauswahl, Einlesen, beide Diagramme, CSV-Export) unter Windows und macOS, je in zwei Browsern.
- [ ] **NFA-13:** Speicherbedarf der Datenverarbeitung < 1 GB, Durchlauf auf einem Notebook mit 8 GB RAM ohne Auslagern. Falls die Übertragung zu langsam ist: Upload als ZIP-Archiv.
- [ ] **NFA-06:** Nachweis mit defekten/leeren Dateien: Meldung statt Abbruch, Oberfläche bleibt bedienbar.
- [ ] **FA-07 / NFA-04, Testprotokoll:** Soll-Ist-Vergleich je ESL-Stichtag aus `python/export/esl_vs_sdat.csv` (wird von `pytest` erzeugt) in die Dokumentation übernehmen. Aktuell: pro Sensor 1 Anker, 31 Prüfpunkte, 12 Stichtage nach Ende der sdat-Daten „nicht prüfbar“.

## 7. Offene Fragen an den Auftraggeber (Kapitel 9, Meeting 30.09.2026)

Nach dem Meeting Antworten hier eintragen und betroffene Punkte oben anpassen.

- [ ] **F3:** Duplikatregel „neuestes `rsm:Creation` gewinnt“ korrekt? → betrifft FA-06
- [ ] **F4:** Ziel-URL und erwartete Antwort für HTTP POST? → betrifft FA-12
- [ ] **F8:** Gewichtung der Verbrauchswerte zwischen zwei Ablesungen gewünscht oder Werte unverändert? → betrifft FA-07, NFA-04
- [ ] **F12:** Öffentliche Bereitstellung auf einer Domain erlaubt? → betrifft FA-14
- [ ] **F13:** Anzeige in UTC oder Lokalzeit (Europe/Zurich)? → betrifft NFA-05, beide Diagramme, Zeitraumauswahl
- [ ] **F14 (neu):** Die sdat-Volumen sind in allen Intervallen genau 3-mal so gross wie die ESL-Differenzen. Skalierungsfaktor, andere Einheit oder Fehler im Beispieldatensatz? → betrifft FA-07, NFA-04, Testprotokoll
- [ ] **F15 (neu):** Akzeptanzkriterium „44 Prüfpunkte“ ist mit dem Datensatz nicht erreichbar, weil die sdat-Daten am 06.09.2021 enden (31 prüfbare Stichtage je Sensor). Kriterium auf „alle ESL-Stichtage im sdat-Zeitraum“ ändern? → betrifft FA-07, NFA-04

## 8. Liefergegenstände ausserhalb des Codes (Kapitel 7)

- [ ] **L1:** Zwischenbericht als PDF + Meeting, Mi 30.09.2026, 09:00
- [ ] Pflichtenheft Version 1.0 nach Klärung der Fragen, zur Unterschrift (Kapitel 10)
- [ ] **L3:** Präsentation inklusive Demo, Fr 02.10.2026, 08:45
- [ ] **L4:** Dokumentation über alle IPERKA-Phasen, Fr 02.10.2026, 12:00. Muss u. a. enthalten: verwendete Rundung und Zahlentypen (NFA-04), Testprotokoll mit Soll-Ist-Vergleich je ESL-Intervall (Kap. 5.5), Entscheid NFA-02 (Variante B).

## 9. Aufräumen

- [ ] **NFA-01, Versionen:** `pyproject.toml` auf `requires-python = ">=3.14"` setzen (aktuell `>=3.10`). `requirements.txt` mit exakten Versionen. In `package.json` `engines.node` auf 24 setzen und `^`-Versionen fixieren; das Paket `cn` prüfen/entfernen.
- [ ] **Kap. 5.3:** Frontend-Abhängigkeiten (Radix, Lucide, Tailwind, shadcn …) im Pflichtenheft ergänzen, da die Liste als abschliessend gilt.
- [ ] Beispieldatensatz lokal: 45 ESL-Files / 44 Stichtage statt 47 / 45 laut Pflichtenheft. Datensatz oder Zahlen im Pflichtenheft prüfen.

## 10. Fehlende Liefergegenstände im Code

- [ ] **FA-11:** Das Klassendiagramm des Datenmodells steht in [PYTHON.md](PYTHON.md) (Kap. 4). Es fehlen noch Klassen für FA-12/FA-13 und ein Komponentendiagramm (Muss).
- [ ] **FA-12 (Nice to have):** HTTP POST an einstellbare URL, Antwortstatus anzeigen. Vorschlag: Funktion `send_json(data, url) -> int` in `export.py`, die `to_json_payload(data)` als Body sendet und den Statuscode zurückgibt; `requests` erst dann in `requirements.txt` aufnehmen.
- [ ] **FA-14 (Nice to have):** öffentliche Bereitstellung, nur nach Zustimmung (F12).

## Erledigt

- [x] **NFA-02 (Variante B):** Klasse `MeterReading(timestamp, consumption, meter_value)` in `analysis.py`, pro Sensor `MeterSeries = dict[datetime, MeterReading]`. `check_series` prüft bei jeder Berechnung: eindeutig, aufsteigend, UTC. `EslMeterReading` nur noch für ESL-Eingabedaten. Tests in `test_analysis.py` und mit echten Daten in `test_esl_vs_sdat.py`.
- [x] **NFA-01, Abhängigkeiten:** `pandas`, `openpyxl`, `fastapi`, `uvicorn`, `python-multipart` entfernt (unbenutzt). `requirements.txt` enthält nur noch `pytest`.
- [x] **NFA-01, Runtime-Versionen v1.0:** `requires-python >=3.14`, Paketversion 1.0.0, `pytest==8.4.2` gepinnt; Node 24 (`engines`, `.nvmrc`), exakte npm-Direct-Deps, `cn` entfernt, `shadcn` nur devDependency; README §5.3-Abgleich und [`docs/ABNAHME_RUNTIME_v1.0.md`](docs/ABNAHME_RUNTIME_v1.0.md).
- [x] **FA-07, Rückwärtsrechnung:** Zählerstände vor dem Anker werden rückwärts berechnet, kein Zeitpunkt geht verloren. Anker = erster ESL-Stichtag im sdat-Zeitraum. Konvention dokumentiert (Stand gilt zu Beginn des Intervalls).
- [x] **FA-07 / NFA-04, Verifikation:** `compare_with_esl` in `analysis.py` und pytest `test_esl_vs_sdat.py` prüfen jeden ESL-Stichtag gegen die Schranke 0.001 kWh und schreiben die Tabelle nach `python/export/esl_vs_sdat.csv`.
- [x] **FA-06:** sdat-Files werden nach `rsm:Creation` (bei Gleichstand Dateiname) eingelesen, der zuletzt gelesene Wert gewinnt.
- [x] **FA-03:** Alle Sensoren werden eingelesen (kein `ALLOWED_SENSOR_IDS` mehr), Zählerstand nur wo ein ESL-Anker existiert.
- [x] **FA-01:** `rsm:Creation` wird eingelesen; `cmd_sort_files` meldet verarbeitete und übersprungene Dateien inkl. Parse-Fehler.
- [x] **FA-02:** ESL `Meter factoryNo` und `status` werden eingelesen, Zeilen mit Status ≠ V übersprungen und gemeldet.
- [x] **NFA-06:** `load_sdat_folder` / `load_esl_folder` fangen Fehler pro Datei ab und melden sie in `skipped`, statt den Lauf abzubrechen.
- [x] **NFA-05:** Tageswerte in `cli._aggregate_by_day` auf lokaler Mitternacht (Europe/Zurich), Ergebnis in UTC; Tests für Winter, Sommer und Zeitumstellung (Commit `5283c46`).
- [x] **NFA-09:** `sort_measured_values_by_time` / `remove_duplicates` stehen nur noch in `sdat.py`.
- [x] **NFA-08:** Keine fest eingetragenen Pfade mehr in `analysis.py` und `compare_esl_vs_sdat.py` (`DATA_DIR` relativ zum Projekt).
- [x] **main.py:** übergibt `DataPoint`-Objekte und einen Dateipfad an `export_json`, der Export läuft wieder (`ID735.csv`, `ID742.csv`, `meter_readings.json`).
- [x] **Tests:** `test_esl.py` auf englische Funktionsnamen umgestellt, Fixtures mit `<Meter>`; `test_analysis.py` mit Tests für FA-07 und NFA-02; Prüfdatensatz für FA-07 vorwärts und rückwärts.
- [x] `python/data/` mit echter ESL-Datei ist nicht mehr im Repository.
- [x] **export.py:** Dataclass `DataPoint` plus Funktionen im Stil von `sdat.py`/`esl.py`; `to_csv_string` / `to_json_payload` / `to_json_string` ohne Dateizugriff; CSV mit 4 Nachkommastellen; JSON-`ts` als Unix-Epoch-String in UTC gemäss Vorgabe des Auftraggebers; Fehler bei Zeitstempel ohne Zeitzone; Prüfung der Sensorkennung.
- [x] **NFA-03 / FA-08:** 15-Minuten-Auflösung nur noch mit Zeitraum von höchstens 31 Tagen (Commit `789a619`).
- [x] **NFA-03:** Zwischenspeicher pro Datensatz, damit nicht jede Anzeige alle Dateien neu einliest (Commit `789a619`, Test `test_cli_cache.py`).
- [x] Next.js: `params` als Promise, `maxBuffer` für grosse Exporte, Prüfung von Datensatz-ID und Sensorkennung, Zeitraumfilter mit UTC-Zeitzone (Commit `02cac85`).
