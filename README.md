# Volt Trace

Webanwendung und Python-Bibliothek zur Auswertung von Schweizer Stromzählerdaten im **SDAT**-Format (relative 15-Minuten-Verbräuche) und **ESL**-Format (absolute Zählerstände an Stichtagen). Aus SDAT und ESL werden fortlaufende Zählerstände berechnet, als Diagramme angezeigt und als CSV exportiert.

---

## Inhalt

- [Überblick](#überblick)
- [Architektur](#architektur)
- [Datenformate](#datenformate)
- [Verarbeitungslogik](#verarbeitungslogik)
- [Projektstruktur](#projektstruktur)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Web-Oberfläche](#web-oberfläche)
- [Python-CLI und Pipeline](#python-cli-und-pipeline)
- [Exportformate](#exportformate)
- [Tests](#tests)
- [Beispieldaten](#beispieldaten)
- [Funktionale Anforderungen (Übersicht)](#funktionale-anforderungen-übersicht)
- [Entwicklung](#entwicklung)

---

## Überblick

| Sensor-ID | Bedeutung | Richtung |
|-----------|-----------|----------|
| **ID742** | Netzbezug | Netz → Gebäude |
| **ID735** | Einspeisung (z. B. Solar) | Gebäude → Netz |

Die Anwendung:

1. nimmt XML-Dateien (SDAT und ESL) per Upload oder Ordnerauswahl entgegen,
2. sortiert sie in `sdat/` und `esl/` Unterordnern,
3. parst und verknüpft die Messreihen,
4. zeigt **Verbrauch** (SDAT-Volumen) oder **Zählerstand** (berechnet) in Diagrammen,
5. exportiert Zählerstände als **CSV** (pro Sensor).

---

## Architektur

```text
┌─────────────────────────────────────────────────────────────┐
│  Next.js (nextjs/) — Browser, Port 3000                     │
│  • Upload, Filter (Sensor, Zeitraum, Auflösung, Diagrammtyp) │
│  • Server Actions + API-Route für CSV-Download              │
└───────────────────────────┬─────────────────────────────────┘
                            │ exec: python -m volt_trace.cli …
                            │ (venv: python/.venv)
┌───────────────────────────▼─────────────────────────────────┐
│  Python (python/volt_trace/)                                │
│  sdat.py → esl.py → analysis.py → export.py                 │
│  cli.py    Schnittstelle für die Web-UI                     │
│  main.py   Batch-Pipeline (Ordner → CSV + JSON auf Disk)    │
└─────────────────────────────────────────────────────────────┘
```

- **Kein separater Python-HTTP-Server** für die Standard-Oberfläche: Next.js startet bei Bedarf Subprozesse (`nextjs/src/lib/python.ts`).
- Hochgeladene Datensätze liegen unter `nextjs/data/<UUID>/` mit Unterordnern `sdat/` und `esl/`.

---

## Datenformate

### SDAT (ValidatedMeteredData, Strom.ch)

Typische Inhalte pro Datei:

- `DocumentID` → Sensor-ID (Suffix nach `_`, z. B. `…_ID735`)
- `Creation`, `Interval` (Start/Ende), `Resolution` (z. B. 15 Minuten)
- `Observation` mit `Sequence` und `Volume` (kWh pro Intervall)

Zeitstempel pro Messwert:

`timestamp = StartDateTime + (Sequence − 1) × Resolution` (in Minuten, UTC).

### ESL (ESLBillingData)

Typische Inhalte:

- `Meter` mit `factoryNo` (wird beim Parsen nicht einzeln gefiltert; relevante OBIS-Werte stammen vom Hauptzähler)
- `TimePeriod end="…"` — Ablesezeitpunkt in **Lokalzeit Europe/Zurich** (ohne `Z`)
- `ValueRow` mit `obis`, `value`, optional `status`

Effektiver Zählerstand pro Richtung:

| Richtung | OBIS Hochtarif | OBIS Niedertarif | Sensor |
|----------|----------------|------------------|--------|
| Bezug | `1-1:1.8.1` | `1-1:1.8.2` | ID742 |
| Einspeisung | `1-1:2.8.1` | `1-1:2.8.2` | ID735 |

Summe **nur**, wenn beide Register (`.1` und `.2`) vorhanden sind. Andere OBIS-Gruppen (z. B. `1-1:1.8.0`) werden ignoriert.

`TimePeriod end` wird nach UTC konvertiert (Winter-/Sommerzeit über `zoneinfo`).

---

## Verarbeitungslogik

### SDAT laden (`load_sdat_folder`)

- Alle `*.xml` in einem Ordner einlesen.
- Pro Datei Sensor-ID extrahieren; aktuell werden nur **ID735** und **ID742** verarbeitet (`ALLOWED_SENSOR_IDS` in `sdat.py`).
- Messwerte gleicher Sensoren aus mehreren Dateien werden zusammengeführt.

### ESL laden (`load_esl_folder`)

- Alle ESL-XMLs einlesen, OBIS-Summen bilden, pro Sensor Stichtagswerte sammeln.
- Doppelte Stichtags-Zeitstempel pro Sensor werden entfernt (`remove_esl_duplicates`).

### Zählerstand berechnen (`calculate_all_meter_readings`)

- Pro Sensor: **frühester** ESL-Stichtag als Referenz (`start_time`, `start_value`).
- Alle SDAT-Messwerte mit `timestamp >= start_time` werden chronologisch kumuliert:  
  `Zählerstand += Volume` je Intervall.
- Sensoren **ohne** ESL-Daten erhalten keine berechnete Zählerstandskurve (`hasMeterReadings: false` in der UI).

### Duplikate (SDAT)

Innerhalb einer Datei und nach dem Zusammenführen: gleicher Zeitstempel → es bleibt der **erste** Eintrag (`remove_duplicates`).  
Eine feinere Regel „alle Files nach `Creation` sortieren, letzter gewinnt“ ist in der Spezifikation beschrieben, aber im Code noch nicht vollständig umgesetzt — bei grossen Produktivdatensätzen kann das relevant sein.

### Rückwärtsrechnung vor dem ESL-Anker

Die aktuelle Implementierung rechnet **vorwärts** ab dem ersten ESL-Stichtag. Punkte **vor** diesem Stichtag werden nicht aus dem Anker zurückgerechnet.

---

## Projektstruktur

```text
volt-trace/
├── README.md
├── nextjs/                    # Next.js 16 Frontend
│   ├── src/app/               # Seite, Upload-Action, CSV-Download-Route
│   ├── src/components/        # Diagramme, FileUpload, UI (shadcn)
│   ├── src/lib/python.ts      # Aufruf von volt_trace.cli
│   └── data/                  # Upload-Datensätze (UUID-Ordner, gitignored)
├── python/
│   ├── volt_trace/
│   │   ├── sdat.py            # SDAT-Parser, MeasuredValue
│   │   ├── esl.py             # ESL-Parser, EslMeterReading, OBIS-Summe
│   │   ├── analysis.py        # Zählerstandsberechnung
│   │   ├── export.py          # CSV- und JSON-Dateiexport
│   │   ├── cli.py             # Kommandos für die Web-UI
│   │   ├── main.py            # CLI-Pipeline mit --esl-dir / --sdat-dir
│   │   └── compare_esl_vs_sdat.py  # Hilfsskript zum Abgleich ESL vs. SDAT
│   ├── tests/                 # pytest (ESL-Fixtures, …)
│   ├── data/                  # Beispiel-ESL-XML
│   └── requirements.txt
└── sdat_files/                # Beispiel-SDAT-XML
```

---

## Voraussetzungen

- **Python** ≥ 3.10 (empfohlen: aktuelle 3.12+ Installation mit `python` im PATH)
- **Node.js** LTS (für Next.js; npm enthalten)
- **Windows / macOS / Linux** — die Pfade in `python.ts` unterstützen Windows-venv und Unix-venv

---

## Installation

Im **Repository-Root** (`volt-trace`, enthält `python/` und `nextjs/`):

### Windows (PowerShell)

```powershell
python -m venv python\.venv
.\python\.venv\Scripts\python -m pip install -r python\requirements.txt
npm --prefix nextjs ci
```

### macOS / Linux

```bash
python3 -m venv python/.venv
./python/.venv/bin/pip install -r python/requirements.txt
npm --prefix nextjs ci
```

Optional Paket im Editable-Modus (für Entwicklung):

```bash
cd python && python -m pip install -e ".[dev]"
```

---

## Web-Oberfläche

### Starten

Im Repository-Root:

```powershell
npm --prefix nextjs run dev
```

Browser: [http://localhost:3000](http://localhost:3000)

Next.js verwendet automatisch `python/.venv` (falls vorhanden), sonst `python`/`python3` aus dem PATH.

### Bedienung

1. **XML-Dateien wählen** oder **Ordner wählen** (nur `.xml`).
2. Unbekannte Dateien werden beim Sortieren übersprungen (Hinweis in der UI).
3. **Sensor**, **Zeitraum (UTC)**, **Auflösung** (Tag / 15 Minuten) und **Diagrammtyp** wählen:
   - **Verbrauch** — SDAT-`Volume` (bei Tag-Ansicht Summe pro Kalendertag).
   - **Zählerstand** — kumulierte absolute Werte aus ESL-Anker + SDAT.
4. **CSV exportieren** — Download über `/download/<datasetId>/<sensorId>` (nur wenn Zählerstände berechenbar sind).

Upload-Grösse: Server Actions erlauben grosse Bodies (`bodySizeLimit` in `next.config.ts`, Standard 120 MB).

---

## Python-CLI und Pipeline

Alle Befehle aus dem Ordner `python/` (mit aktivierter venv oder `python -m`):

### Web-Schnittstelle (`volt_trace.cli`)

| Kommando | Argumente | Ausgabe |
|----------|-----------|---------|
| `sort-files` | `<srcDir> <datasetDir>` | JSON: Dateien nach `sdat/` / `esl/` verschieben |
| `sensors` | `<datasetDir>` | JSON: Sensorliste inkl. `hasMeterReadings` |
| `series` | `<datasetDir> <sensorId> <kind> <resolution> <from> <to>` | JSON-Zeitreihe (`kind`: `consumption` \| `meter-reading`, `resolution`: `day` \| `15min`) |
| `export` | `<datasetDir> <sensorId>` | CSV auf stdout (`timestamp,value`) |

Beispiel:

```bash
cd python
python -m volt_trace.cli sensors ../nextjs/data/<UUID>
```

### Batch-Pipeline (`volt_trace.main`)

Liest zwei Ordner, berechnet Zählerstände, schreibt **CSV und JSON** nach `--output-dir`:

```bash
cd python
python -m volt_trace.main --esl-dir pfad/zu/esl --sdat-dir pfad/zu/sdat --output-dir export
```

### Abgleich ESL vs. SDAT

`compare_esl_vs_sdat.py` vergleicht Differenzen zwischen ESL-Stichtagen und summierten SDAT-Volumina (lokales Hilfsskript, nicht Teil der Web-UI).

---

## Exportformate

### CSV (Pflicht)

- Eine Datei pro Sensor: `ID742.csv`, `ID735.csv`
- Header: `timestamp,value`
- `timestamp`: Unix-Sekunden, UTC
- `value`: absoluter Zählerstand (Float, Punkt als Dezimaltrennzeichen)
- Komma als Feldtrennzeichen

Implementierung: `export.py` (`export_csv`); Web-Download via `cli export`.

### JSON (Nice-to-have)

- `export_json` in `export.py` schreibt pro Sensor eine JSON-Datei mit Struktur  
  `[{ "sensorId": "…", "data": [{ "ts": "<ISO8601>", "value": … }] }]`
- **HTTP POST** an einen externen Server ist in den Modul-Kommentaren spezifiziert, aber **noch nicht implementiert**.

---

## Tests

```bash
cd python
python -m pytest -q
```

- `tests/test_esl.py` — OBIS-Gruppierung, Hoch-/Niedertarif-Summe, UTC-Konvertierung, fehlende Register
- `tests/fixtures/` — minimale ESL-XMLs

Hinweis: Funktionsnamen in `esl.py` heissen `_obis_group` und `_total_readings_by_obis_group`; Tests müssen dieselben Namen importieren, damit pytest grün läuft.

---

## Beispieldaten

| Pfad | Inhalt |
|------|--------|
| `sdat_files/*.xml` | SDAT-Beispiel (ID735, 15-Min-Intervall) |
| `python/data/EdmRegisterWertExport_*.xml` | ESL mit Zähler `38157930`, OBIS 1.8.x / 2.8.x |

Für End-to-End-Tests: SDAT- und ESL-Ordner mit passenden Sensor-IDs und überlappendem Zeitraum verwenden.

---

## Funktionale Anforderungen (Übersicht)

Kurzstatus gegen die Seminar-Spezifikation (ohne Gewähr auf Vollständigkeit der Abnahme):

| ID | Thema | Status im Repo |
|----|--------|----------------|
| FA-01 | SDAT einlesen | Kernfelder ja; `Creation`/Merge-Regel teilweise |
| FA-02 | ESL einlesen | `end`, OBIS, `value` ja; `factoryNo`/`status` nicht modelliert |
| FA-03 | Sensoren / UI | UI für ID735/742; weitere IDs nur wenn in SDAT und Parser erlaubt |
| FA-04 | OBIS-Summe HT+NT | Implementiert in `esl.py` |
| FA-05 | Zeitstempel aus Sequence | Implementiert in `sdat.py` |
| FA-06 | Duplikate nach Creation | Vereinfacht (erster Timestamp gewinnt) |
| FA-07 | Zählerstand Anker + Konsistenz | Vorwärts ab frühestem ESL; keine Rückwärtsrechnung / ESL-Toleranztests |
| FA-08–09 | Verbrauchs- / Zählerstandsdiagramm | Web-UI mit Recharts |
| FA-10 | CSV-Export | Ja (CLI + Download) |
| FA-11 | Klassen-/Komponentendiagramm | Dokumentation ausserhalb des Repos |
| FA-12–13 | JSON HTTP POST / JSON-Datei | JSON-Datei via `main.py`; HTTP POST offen |

---

## Entwicklung

```bash
# Typecheck Frontend
npm --prefix nextjs run typecheck

# Produktionsbuild
npm --prefix nextjs run build
npm --prefix nextjs run start
```

Python-Abhängigkeiten: `pandas`, `openpyxl` (pyproject.toml); `requirements.txt` enthält zusätzlich pytest und FastAPI-Pakete für mögliche Erweiterungen.

### Wichtige Erweiterungspunkte

- SDAT-Deduplizierung über alle Dateien nach `Creation` (aufsteigend), letzter Wert gewinnt
- Rückwärtsrechnung und Validierung an allen ESL-Stichtagen (&lt; 0,001 kWh)
- Generische Sensor-IDs (nicht nur ID735/ID742)
- HTTP-POST-Export (FA-12) und einheitliches JSON-Schema zwischen Export und API

---

## Lizenz / Autoren

Seminarprojekt **volt-trace** — Version siehe `python/volt_trace/__init__.py` (`__version__`).
