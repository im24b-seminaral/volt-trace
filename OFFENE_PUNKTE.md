# Offene Punkte – Volt Trace

Was laut **Pflichtenheft v1.0** (Gruppe 3, Energieagentur Bünzli) noch fehlt oder geklärt werden muss. Python-Details: [PYTHON.md](PYTHON.md). Architekturdiagramme: [docs/architecture/](docs/architecture/). Web/README: Issue **#12**; Abnahmetests: **#15** (`docs/acceptance/`).

**Dokumentationsstand (Codeabgleich):** Git-Commit `387b998` · Referenzen FA/NFA = Pflichtenheft v1.0

## 1. Fachlogik Python (Muss)

- [ ] **Faktor 3 / ESL vs. SDAT (F14).** Zwischen ESL-Stichtagen kann die Summe der SDAT-Volumen deutlich von der ESL-Differenz abweichen (im Beispieldatensatz oft Faktor ~3). **Keine** automatische Skalierung oder Gewichtung in v1.0. `compare_with_esl` / `test_esl_vs_sdat.py` können am vollständigen Datensatz scheitern — Klärung mit Auftraggeber, nicht still im Code „korrigieren“.
- [x] **FA-05:** Intervallende, Unit `MIN`, Sequenzvalidierung, Tagesaggregation Mitternacht → Vortag.
- [x] **FA-07 (Basis):** `calculate_meter_readings` vorwärts/rückwärts ab Anker; `compare_with_esl` mit Toleranz 0,001 kWh; Konvention **Intervallende** (FA-05). **Nicht** Teil der v1.0-UI: Zählerstands-Diagramm und CSV `zaehlerstand` zeigen **ESL-Ablesungen**, nicht die berechnete `MeterSeries`.
- [ ] **FA-07 (optional / F8):** Gewichtung, Neuansatz an jedem ESL-Stichtag, Intervall-Faktoren — nur nach Entscheid Auftraggeber; nicht als offene Muss-Implementierung führen.
- [ ] **FA-01:** Unterordner rekursiv lesen (`glob("*")` / flaches `*.xml` in Loadern und `cmd_sort_files`).

## 2. Performance und Architektur

- [ ] **NFA-03:** Erstes Einlesen weiterhin zu langsam (Ziel Lesen ≤ 10 s); Cache `.processed-v2.cache` beschleunigt Folgeaufrufe.
- [ ] **NFA-03:** Fortschrittsanzeige beim Upload/Einlesen.
- [x] **NFA-01 / NFA-11 (Architektur v1.0):** Kein FastAPI/uvicorn; Next.js ruft `python -m volt_trace.cli` per Subprozess auf (**127.0.0.1**). Dokumentiert in [PYTHON.md](PYTHON.md) und [docs/architecture/component-diagram.mmd](docs/architecture/component-diagram.mmd).
- [ ] **NFA-01 (OO-Modell):** Kein separates Service-Klassenlayer — Funktionen + Dataclasses (#12, nicht #14). Keine Pflicht, das in dieser Abgabe umzubauen.
- [ ] **NFA-02 (Bericht):** Entscheid Variante B (`dict[datetime, MeterReading]`) im Projektbericht gegenüber Pflichtenheft-`TreeMap` festhalten.

## 3. Frontend (#11 / #12)

- [ ] **FA-08 / FA-09:** Bezug und Einspeisung als getrennte Reihen im selben Diagramm.
- [ ] **FA-08 / FA-09:** Achsentitel vs. Chart-Titel — Abnahmefrage.
- [ ] **FA-13:** JSON-Download in der UI (Backend: `to_json_string` in `export.py`; CLI-Kommando optional #12).

## 4. Sicherheit und Datenschutz

- [x] **NFA-12:** Sitzung `vt_session`, `VOLT_TRACE_DATA_DIR`, Cleanup, Eigentümerschaft.
- [x] **NFA-11 / NFA-12:** Loopback-only Next.js; Python ohne Netzwerkport.

## 5. Tests (Kap. 5.5)

- [x] **FA-05:** `test_sdat_timestamps.py`, `test_daily_aggregation.py`, `test_quantities.py` (Quelle: `python/tests/`).
- [ ] **FA-06:** Dedizierte pytest-Abdeckung „neuestes Creation gewinnt“ fehlt (Logik in `load_sdat_folder` vorhanden).
- [ ] **FA-10:** Kein `test_export.py` mit CSV-Contract; Export läuft über `export.py` + `cli`/`main` (manuell / #15).

## 6. Nachweise für die Abnahme (#15)

- [ ] **NFA-03, NFA-07, NFA-08, NFA-13, NFA-06:** siehe `docs/acceptance/` wenn vorhanden; nicht hier ohne Messprotokoll behaupten.
- [ ] **FA-07 Testprotokoll:** `esl_vs_sdat.csv` aus `test_esl_vs_sdat.py` nur wenn Beispieldaten `XML-Files/` vorhanden.

## 7. Offene Fragen an den Auftraggeber

- [ ] **F3:** Duplikatregel Creation → FA-06
- [ ] **F4:** HTTP POST Ziel → FA-12 (Nice-to-have)
- [ ] **F8:** Gewichtung ja/nein → optional FA-07
- [ ] **F12 / FA-14:** Öffentliche Domain
- [x] **F13 (Umsetzung Anzeige):** Diagramm/Zeitraum **Europe/Zurich** in Next.js (#12 README); API/CSV weiter UTC — siehe PYTHON.md
- [ ] **F14:** Faktor 3 im Beispieldatensatz
- [ ] **F15:** Anzahl Prüfpunkte vs. sdat-Ende 2021

## 8. Liefergegenstände ausserhalb des Codes

Unverändert (PDF, Präsentation, IPERKA-Doku L4 …).

## 9. Aufräumen / Pflichtenheft-Text

- [x] **Runtime v1.0** (Python 3.14, Node 24): siehe „Erledigt“ und `docs/ABNAHME_RUNTIME_v1.0.md`.
- [ ] **Kap. 5.3:** Frontend-Stack im Pflichtenheft ergänzen.
- [ ] Beispieldatensatz: Anzahl ESL-Dateien vs. Pflichtenheftzahl.

## 10. Liefergegenstände Diagramme (FA-11)

- [x] **FA-11:** Klassen- und Komponentendiagramm unter [docs/architecture/](docs/architecture/) (#14); Abgleich mit Commit `387b998`.
- [ ] **FA-12 (Nice to have):** HTTP POST (`send_json`), UI-Status — optional.
- [ ] **FA-14 (Nice to have):** öffentlicher Betrieb nach F12.

## 11. Befunde an #12 (nur Lesen in #14 — keine Code-Änderung hier)

- **README** mit tatsächlicher CLI (`export … verbrauch|zaehlerstand`), Session, `hasConsumption`/`hasMeterReadings` synchron halten.
- **FA-01** rekursive Ordner; ggf. Upload ZIP (NFA-13).
- **FA-08** Multi-Sensor-Diagramm; Export-Links für beide CSV-Arten in der UI.
- **Integrationstests** Download-Route + `kind`-Parameter; formale FA-10-Tests.
- **NFA-01 OO** nur falls Auftraggeber/Pflichtenheft es weiter verlangt — nicht Dokumentationsblocker.

## Erledigt

- [x] **NFA-02 (Variante B):** `MeterReading`, `MeterSeries` Typalias, `check_series`.
- [x] **NFA-04 (teilweise):** `quantities.py`, 4 Dezimalstellen, ESL-Toleranz 0,001 kWh.
- [x] **NFA-09 / FA-10:** `cmd_export` nutzt `export.py` (`consumption_points` / `meter_points`, `kind` `verbrauch`/`zaehlerstand`); getrennte CSV-Dateinamen; `main.py` gleiche Logik.
- [x] **FA-06:** Einlesen nach `rsm:Creation`, last wins in `load_sdat_folder`.
- [x] **FA-03:** Alle SDAT-Sensoren; ESL für Zählerstands-Anzeige.
- [x] **FA-01/02, NFA-06, NFA-05, NFA-08, NFA-03 Cache,** Runtime v1.0, Next.js-Basics — wie zuvor dokumentiert.
- [x] **FA-07 / NFA-04 Verifikation:** `compare_with_esl`, `test_esl_vs_sdat.py` (mit Datensatz).
- [x] **FA-07 Rückwärtsrechnung:** Anker erster ESL im sdat-Zeitraum; Zeitstempel = **Intervallende** (konsistent mit FA-05).
- [x] **export.py:** `DataPoint`, JSON/CSV-Helfer, `export_esl_comparison_csv`.
- [x] **main.py:** Batch-CSV Verbrauch + ESL-Zählerstand (keine berechnete MeterSeries-JSON-Pipeline mehr).
