# Volt Trace

Webanwendung und Python-Bibliothek zur Auswertung von Schweizer Stromzählerdaten im **SDAT**-Format (relative 15-Minuten-Verbräuche) und **ESL**-Format (absolute Zählerstände an Stichtagen). Der Verbrauch kommt aus SDAT, die Zählerstände kommen **direkt aus ESL** (keine Umrechnung aus SDAT). Beides wird als Diagramm angezeigt und getrennt als CSV exportiert.

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

Weitere Sensoren aus SDAT (im Beispieldatensatz `ID26256`, `ID26257`, `ID26263`) werden ebenfalls eingelesen und mit Richtung `other` geführt. ESL-Zählerstände gibt es nur für ID742 und ID735.

Die Anwendung:

1. nimmt XML- und ZIP-Dateien oder einen ganzen Ordner (inklusive Unterordnern) entgegen,
2. sortiert die Dateien in `sdat/` und `esl/` und zeigt einen **Importbericht** (gefunden, eingelesen, übersprungen, Gründe, Befunde),
3. liest die Messreihen ein: Verbrauch aus SDAT, Zählerstände aus ESL, je Sensor eindeutig und nach Zeit sortiert (UTC),
4. zeigt **Verbrauch** (SDAT, Balken) oder **Zählerstand** (ESL, Punkte mit Linie) für einen oder mehrere Sensoren im selben Diagramm,
5. exportiert pro Sensor `<Sensor>_verbrauch.csv` (FA-10a) und, falls ESL vorhanden, `<Sensor>_zaehlerstand.csv` (FA-10b).

---

## Architektur

```text
┌─────────────────────────────────────────────────────────────┐
│  Next.js (nextjs/) — Browser, Port 3000                     │
│  • Upload (XML/ZIP/Ordner), Importbericht                   │
│  • Filter: Diagramm, Sensoren, Zeitraum                     │
│  • Server Action (Upload) + Route für CSV-Download          │
└───────────────────────────┬─────────────────────────────────┘
                            │ execFile: python -m volt_trace.cli …
                            │ (venv: python/.venv, Timeout 180 s)
┌───────────────────────────▼─────────────────────────────────┐
│  Python (python/volt_trace/)                                │
│  sdat.py / esl.py  → einlesen (SDAT-Verbrauch, ESL-Stände)  │
│  export.py         → CSV (verbrauch / zaehlerstand), JSON   │
│  cli.py            Schnittstelle für die Web-UI, Import     │
│  main.py           Batch: Ordner → CSV-Dateien              │
│  analysis.py       nur Prüfung SDAT vs. ESL (Befund, Tests) │
└─────────────────────────────────────────────────────────────┘
```

- **Kein separater Python-HTTP-Server** für die Standard-Oberfläche: Next.js startet bei Bedarf Subprozesse (`nextjs/src/lib/python.ts`).
- Hochgeladene Datensätze liegen **nur zur Laufzeit** unter dem konfigurierbaren Datenverzeichnis (Standard: OS-Temp `volt-trace-data/<UUID>/` mit `sdat/`, `esl/`, `import-report.json` und `.processed-v3.cache`), nicht im Git-Repository.
- Jede Browser-Sitzung (`vt_session`-Cookie) darf nur eigene Dataset-IDs lesen/exportieren; Verarbeitung erfolgt ausschließlich lokal (Next.js + Python-Subprozess, kein Netzwerkport in Python).

---

## Datenformate

### SDAT (ValidatedMeteredData, Strom.ch)

Typische Inhalte pro Datei:

- `DocumentID` → Sensor-ID (Suffix nach `_`, z. B. `…_ID735`)
- `Creation`, `Interval` (Start/Ende), `Resolution` (z. B. 15 Minuten)
- `Observation` mit `Sequence` und `Volume` (kWh pro Intervall)

Zeitstempel pro Messwert (FA-05):

`timestamp = StartDateTime + Sequence × Resolution` — **Intervallende** in UTC. Verbrauchsfilter in der API: `(Beginn, Ende]` (Grenze Beginn exklusiv, Ende inklusiv).

Prüfungen beim Einlesen (NFA-06): Als `Unit` ist nur `MIN` erlaubt. Anzahl der Messwerte, höchste `Sequence` und `(Ende − Beginn) / Auflösung` müssen übereinstimmen, die Sequenzen müssen lückenlos `1..N` sein. Fehlt `Resolution` (Schema 1p5), wird die Auflösung aus `(Ende − Beginn) / Anzahl Messwerte` berechnet. Eine fehlerhafte Datei wird mit Grund im Importbericht übersprungen, der Rest wird weiter verarbeitet.

### ESL (ESLBillingData)

Typische Inhalte:

- `Meter` mit `factoryNo`. Pro Datei liefert der erste Zähler mit einer OBIS-Gruppe diese Gruppe; Zähler ohne vollständige Paare (im Beispiel `5442313`) werden mit Grund als `meter`-Eintrag gemeldet.
- `TimePeriod end="…"` — Ablesezeitpunkt in **Lokalzeit Europe/Zurich** (ohne `Z`)
- `ValueRow` mit `obis`, `value`, optional `status`. Zeilen mit `status` ungleich `V` werden übersprungen und als Datensatz-Skip (`record`) mit OBIS und Status gemeldet.

Datei, Zählernummer, `end` und alle `ValueRow`s bleiben als Herkunftsdaten (`EslSource`) am Messwert erhalten.

Effektiver Zählerstand pro Richtung:

| Richtung | OBIS Hochtarif | OBIS Niedertarif | Sensor |
|----------|----------------|------------------|--------|
| Bezug | `1-1:1.8.1` | `1-1:1.8.2` | ID742 |
| Einspeisung | `1-1:2.8.1` | `1-1:2.8.2` | ID735 |

Summe **nur**, wenn beide Register (`.1` und `.2`) vorhanden sind. Andere OBIS-Gruppen (z. B. `1-1:1.8.0`) werden ignoriert.

`TimePeriod end` wird nach UTC konvertiert (Winter-/Sommerzeit über `zoneinfo`).

---

## Verarbeitungslogik

### Import (`cli.py sort-files`)

- Durchsucht den Upload-Ordner **rekursiv**. ZIP-Archive (auch in Unterordnern) werden sicher entpackt: keine absoluten Pfade, kein `..`, keine symbolischen Links, höchstens 20 000 Einträge, 256 MB pro Eintrag und 1 GB gesamt. `__MACOSX`, `._*` und `.DS_Store` werden ignoriert.
- Jede Datei wird am Wurzelelement erkannt (SDAT: Namensraum `http://www.strom.ch`, ESL: `ESLBillingData`) und mit ihrem **relativen Pfad** nach `sdat/` bzw. `esl/` verschoben. Gleichnamige Dateien aus verschiedenen Unterordnern gehen so nicht verloren.
- Nicht-XML, ungültiges XML, unbekanntes Format, ungültige ZIPs und unvollständige Dateien landen mit Grund im Bericht; alle gültigen Dateien werden trotzdem eingelesen (NFA-06).

### SDAT laden (`load_sdat_folder`)

- XML-Dateien auch in Unterordnern einlesen.
- Pro Datei Sensor-ID aus `DocumentID` extrahieren; auch weitere Sensoren werden eingelesen.
- Messwerte gleicher Sensoren aus mehreren Dateien werden zusammengeführt.
- Dateiquelle, `DocumentID`, `Creation`, Intervall, Auflösung mit Einheit und Dokumentstatus bleiben als `SdatSource` im Datenmodell erhalten.

### ESL laden (`load_esl_folder`)

- ESL-XMLs auch in Unterordnern einlesen, OBIS-Summen bilden, pro Sensor Stichtagswerte sammeln. Meter, OBIS-Werte und Status bleiben als Herkunftsdaten erhalten.
- Doppelte Stichtags-Zeitstempel pro Sensor werden entfernt (`remove_esl_duplicates`, die nach Pfad zuerst gelesene Datei gewinnt), danach wird nach Zeit sortiert.
- Diese ESL-Werte sind **direkt** die Quelle für das Zählerstandsdiagramm und den Export `zaehlerstand`. Sie werden nie aggregiert, skaliert oder an SDAT angepasst.

### Duplikate (SDAT, FA-06)

Innerhalb einer Datei müssen die Sequenznummern vollständig und eindeutig sein. Über mehrere Dateien hinweg gewinnt bei gleichem Zeitstempel der Wert aus der zuletzt erstellten Datei (`Creation`); bei gleichem `Creation` entscheidet der relative Dateipfad.

### Prüfung SDAT gegen ESL (`analysis.py`)

`analysis.py` rechnet aus einem ESL-Anker und den SDAT-Volumen Zählerstände vorwärts und rückwärts (FA-07). Diese berechnete Serie wird **nicht** angezeigt und nicht exportiert. Sie dient nur noch zwei Zwecken:

- **Befund im Importbericht:** Ist die berechnete Zunahme zwischen zwei ESL-Stichtagen etwa dreimal so gross wie die ESL-Differenz, meldet der Import «SDAT-Verbrauch und ESL-Zählerdifferenz weichen bei der Testanlage um etwa Faktor 3 ab». Die Werte bleiben unverändert.
- **Tests:** `test_analysis.py` und `test_esl_vs_sdat.py`. Der Soll-Ist-Test gegen ESL ist wegen dieses Faktors als `xfail` markiert.

---

## Projektstruktur

```text
volt-trace/
├── README.md                  # dieses Dokument
├── PYTHON.md                  # ausführliche Doku des Python-Teils
├── OFFENE_PUNKTE.md           # offene Punkte gegen das Pflichtenheft
├── docs/
│   ├── architecture/          # Klassen- und Komponentendiagramm (FA-11)
│   └── ABNAHME_RUNTIME_v1.0.md
├── XML-Files/                 # Beispieldaten, nur lokal (in .gitignore)
│   ├── SDAT-Files/
│   └── ESL-Files/
├── nextjs/                    # Next.js 16 Frontend
│   ├── src/app/
│   │   ├── page.tsx           # Hauptseite: Importbericht, Filter, Diagramm, CSV-Buttons
│   │   ├── actions.ts         # Server Action uploadDataset (Upload → sort-files)
│   │   └── download/[datasetId]/[sensorId]/route.ts   # CSV-Download
│   ├── src/components/
│   │   ├── FileUpload.tsx     # XML/ZIP- und Ordnerauswahl
│   │   ├── ImportReport.tsx   # Importbericht aus import-report.json
│   │   ├── ChartFilters.tsx   # Diagrammart, Sensoren, Zeitraum, Schnellwahl
│   │   ├── ChartForm.tsx      # Formular + Ladezustand
│   │   ├── EnergyChart.tsx    # Recharts-Diagramm (Balken bzw. Linie, mehrere Sensoren)
│   │   ├── ConsumptionChart.tsx / MeterReadingChart.tsx
│   │   └── ui/                # shadcn-Komponenten
│   ├── src/lib/
│   │   ├── python.ts          # Aufruf von volt_trace.cli (Timeout, Fehlertext)
│   │   ├── datetime.ts        # Europe/Zurich ↔ UTC, Achsenbeschriftung
│   │   ├── session*.ts, data-paths.ts, runtime-data.ts   # Sitzung und Datenverzeichnis
│   │   └── types.ts           # Sensor, SensorSeries, ImportReport …
│   ├── src/middleware.ts      # setzt Sitzungs-Cookie
│   ├── tests/charts/          # Diagramm- und datetime-Tests (node:test)
│   └── (kein data/ im Repo; Laufzeit unter VOLT_TRACE_DATA_DIR / OS-Temp)
└── python/
    ├── volt_trace/
    │   ├── sdat.py            # SDAT-Parser: MeasuredValue, SdatSource, SdatDataset
    │   ├── esl.py             # ESL-Parser: EslMeterReading, EslSource, EslDataset, OBIS-Summe
    │   ├── quantities.py      # round_kwh / sum_kwh (4 Nachkommastellen, NFA-04)
    │   ├── export.py          # CSV (verbrauch / zaehlerstand) und JSON
    │   ├── cli.py             # Kommandos für die Web-UI inkl. Import und Cache
    │   ├── main.py            # Batch-Export mit --esl-dir / --sdat-dir
    │   ├── analysis.py        # Prüfung SDAT vs. ESL (Befund, Tests)
    │   ├── compare_esl_vs_sdat.py  # Hilfsskript zum Abgleich ESL vs. SDAT
    │   └── calc_values.py     # Hilfsskript: Kennzahlen für die Doku
    ├── tests/                 # pytest + fixtures/ (ESL-Beispiele)
    ├── pyproject.toml
    └── requirements.txt
```

---

## Voraussetzungen

| Komponente | Version (v1.0) |
|------------|----------------|
| **Python** | **3.14+** ([`python/pyproject.toml`](python/pyproject.toml), [`python/.python-version`](python/.python-version)) |
| **Node.js** | **24.x LTS** ([`nextjs/package.json`](nextjs/package.json) `engines`, [`nextjs/.nvmrc`](nextjs/.nvmrc)) |
| **npm** | `npm ci` im Ordner `nextjs` |

Plattformen: **Windows / macOS / Linux**. Node **22** oder älter löst bei `npm ci` eine `EBADENGINE`-Warnung aus; für Abnahme ist **Node 24** vorgeschrieben.

### Abhängigkeiten v1.0 (Abgleich Pflichtenheft §5.3)

| Rolle | Pakete |
|-------|--------|
| Python Runtime | nur Standardbibliothek im Paket `volt_trace` |
| Python Dev/Test | `pytest==8.4.2` ([`python/requirements.txt`](python/requirements.txt)) |
| Frontend Runtime | Next.js, React, Radix UI, Recharts, Lucide, Tailwind (via PostCSS), `clsx`, `class-variance-authority`, `tailwind-merge`, `tw-animate-css` — siehe [`nextjs/package.json`](nextjs/package.json) `dependencies` |
| Generator/Build | `shadcn` (CLI), TypeScript, `@tailwindcss/postcss`, `tailwindcss` — nur `devDependencies` |
| Nicht erlaubt / ungenutzt | pandas, openpyxl, FastAPI, uvicorn, `cn`, `requests` (bis FA-12) |

Direkte npm-/pip-Versionen sind **exakt** gepinnt; transitive Abhängigkeiten stehen im Lockfile.

---

## Installation

Im **Repository-Root** (`volt-trace`, enthält `python/` und `nextjs/`):

### Windows (PowerShell)

```powershell
python -m venv python\.venv
.\python\.venv\Scripts\python -m pip install -r python\requirements.txt
.\python\.venv\Scripts\python -m pip install -e python
npm --prefix nextjs ci
```

### macOS / Linux

```bash
python3 -m venv python/.venv
./python/.venv/bin/pip install -r python/requirements.txt
./python/.venv/bin/pip install -e python
npm --prefix nextjs ci
```

Verifikation und Plattformnachweise: [`docs/ABNAHME_RUNTIME_v1.0.md`](docs/ABNAHME_RUNTIME_v1.0.md).

---

## Web-Oberfläche

### Starten

Im Repository-Root:

```powershell
npm --prefix nextjs run dev
```

Browser: [http://127.0.0.1:3000](http://127.0.0.1:3000) (Dev- und Produktionsstart binden nur an **127.0.0.1**, kein LAN-Zugriff).

Next.js verwendet automatisch `python/.venv` (falls vorhanden), sonst `python`/`python3` aus dem PATH.

### Bedienung

1. **XML/ZIP-Dateien wählen** oder **Ordner wählen** (inklusive Unterordnern). Während des Uploads zeigt der Button «Lade hoch …». Liefert der Import keine einzige verwendbare Datei, erscheint der erste Grund als Fehlermeldung und es wird kein Datensatz angelegt.
2. Der **Importbericht** zeigt gefundene, eingelesene und übersprungene Dateien sowie übersprungene Datensätze. Unter «Meldungen und Gründe» stehen alle Einträge mit Datei, Zähler, OBIS und Grund. Der bekannte Faktor-3-Befund der Testanlage erscheint als Hinweis.
3. Filter wählen und **Anzeigen** klicken:
   - **Diagramm:** **Verbrauch** (SDAT-`Volume`, Balken; bei mehreren Sensoren gestapelt) oder **Zählerstand** (ESL-Ablesungen, jeder Punkt markiert und linear verbunden).
   - **Sensoren:** ein oder mehrere Sensoren per Checkbox; mehrere erscheinen als getrennte Reihen im selben Diagramm.
   - **Zeitraum:** **Von** / **Bis** als Kalendertage in **Europe/Zurich** oder Schnellwahl **7 Tage**, **Monat**, **Jahr**, **Alles**. Ohne Auswahl gilt der ganze Datenzeitraum der gewählten Sensoren.
   - **Auflösung:** wird automatisch gewählt. Bis 7 Tage zeigt der Verbrauch 15-Minuten-Werte, darüber Tageswerte (Summe pro Kalendertag). ESL-Zählerstände werden nie aggregiert.
4. **CSV laden:** Unter dem Diagramm stehen pro gewähltem Sensor die Buttons **Verbrauch (CSV)** (nur mit SDAT-Daten) und **Zählerstände (CSV)** (nur mit ESL-Daten). Download über `/download/<datasetId>/<sensorId>?kind=verbrauch|zaehlerstand`, Dateiname `<Sensor>_verbrauch.csv` bzw. `<Sensor>_zaehlerstand.csv`.

Fehler aus Python (z. B. Zeitüberschreitung nach 180 s) werden als Text angezeigt; der Upload kann ohne Neuladen erneut gestartet werden.

### Zeitzone in der Oberfläche

- Diagramm-Achse und Tooltips zeigen Zeitstempel in **Europe/Zurich** (`DD.MM.YYYY` bzw. `DD.MM.YYYY HH:mm`).
- Die API liefert weiterhin UTC-ISO-Strings; die Umrechnung erfolgt in [`nextjs/src/lib/datetime.ts`](nextjs/src/lib/datetime.ts).
- Datumsfilter (**Von** / **Bis**) bezeichnen lokale Kalendertage in Zurich und werden für die Python-Abfrage in UTC umgerechnet. Beim Verbrauch geht der Zeitraum von lokaler Mitternacht des Von-Tags (exklusiv) bis zur **abschliessenden** lokalen Mitternacht nach dem Bis-Tag (inklusiv), damit der Wert mit Intervallende 00:00 zum richtigen Tag gehört (`localNextDayStartUtcIso`). Beim Zählerstand gilt Von-Tag 00:00 bis Bis-Tag 23:59:59.
- Wiederholte Uhrzeiten bei der Umstellung auf Winterzeit sind in der 15-Minuten-Ansicht durch den UTC-Versatz unterscheidbar (`GMT+2` / `GMT+1`).
- **CSV-Export** bleibt unverändert: Unix-Zeitstempel in **UTC** (Sekunden).

Upload-Grösse: Server Actions erlauben grosse Bodies (`bodySizeLimit` in `next.config.ts`; jeder Python-Aufruf bricht nach 180 s ab, siehe `nextjs/src/lib/python.ts`; Standard 120 MB).

### Sitzung und Datenschutz (NFA-11 / NFA-12)

- **Keine Konten:** Zugriff über HttpOnly-Cookie `vt_session` (Session-Cookie, endet mit dem Browser-Tab bzw. Browser-Sitzung).
- **Eigentümerschaft:** `?dataset=<UUID>` allein reicht nicht — Diagramm und CSV prüfen, ob die UUID zur aktuellen Sitzung gehört (fremde IDs → Fehlermeldung bzw. HTTP 403 beim Export).
- **Speicherort:** `VOLT_TRACE_DATA_DIR` (optional); sonst `%TEMP%/volt-trace-data` (Windows) bzw. `/tmp/volt-trace-data` (Unix).
- **Aufräumen:** Fehlgeschlagene Uploads löschen den Dataset-Ordner; abgelaufene Sitzungen (Idle-TTL, Standard 4 h, `SESSION_IDLE_TTL_MS`) werden beim nächsten Request bereinigt (`_sessions/*.json` + zugehörige Datensätze inkl. Cache).
- **Abnahme (manuell):** Zwei Browser-Profile mit gleicher Dataset-URL → nur Besitzer sieht Daten; nach Cookie-Löschen/TTL keine XML/Cache-Reste unter `VOLT_TRACE_DATA_DIR`; `next build` ohne Tracing-Warnung zu tausenden Dateien im Projektbaum.

---

## Python-CLI und Pipeline

Alle Befehle aus dem Ordner `python/` (mit aktivierter venv oder `python -m`):

### Web-Schnittstelle (`volt_trace.cli`)

| Kommando | Argumente | Ausgabe |
|----------|-----------|---------|
| `sort-files` | `<srcDir> <datasetDir>` | JSON-Importbericht (siehe unten); verschiebt Dateien rekursiv nach `sdat/` / `esl/`, entpackt ZIPs und füllt den Cache |
| `sensors` | `<datasetDir>` | JSON: Sensorliste (Vereinigung aus SDAT und ESL) |
| `series` | `<datasetDir> <sensorId> <kind> <resolution> <from> <to>` | JSON `[{sensorId, data: [{ts, value}]}]` (`kind`: `consumption` \| `meter-reading`, `resolution`: `day` \| `15min`, `ts` ISO-UTC) |
| `export` | `<datasetDir> <sensorId> <kind>` | CSV auf stdout (`timestamp,value`), `kind`: `verbrauch` \| `zaehlerstand`. Exit-Code `1`, wenn es für den Sensor keine Daten dieser Art gibt, `2` bei unbekanntem `kind` |

**Importbericht** von `sort-files`:

| Feld | Bedeutung |
|------|-----------|
| `foundFiles` | gefundene Dateien inkl. ZIP-Einträge (ohne `__MACOSX`, `._*`, `.DS_Store`) |
| `processedFiles` | erfolgreich eingelesene XML-Dateien |
| `skippedFiles` | `foundFiles − processedFiles` |
| `skippedRecords` | übersprungene Datensätze (z. B. ESL-Zeilen mit Status ≠ `V`) |
| `issues` | Liste `{file, kind, reason, skippedRecords, meter?, obis?, status?}`; `kind` ist `file`, `record` oder `meter` |
| `findings` | Hinweise, z. B. der Faktor-3-Befund der Testanlage |

Next.js speichert den Bericht als `import-report.json` im Datensatz.

**Sensorliste** von `sensors`: `sensorId`, `label`, `direction` (`consumption` \| `feed-in` \| `other`), `hasConsumption` (SDAT vorhanden), `hasMeterReadings` (ESL vorhanden), `consumptionDates` und `meterReadingDates` (`[erster, letzter]` lokaler Tag, für die Vorbelegung des Zeitraums).

**Zeitraum** von `series`: Verbrauch `from < ts ≤ to`, Zählerstand `from ≤ ts ≤ to`. Bei `resolution=day` wird nur der Verbrauch je lokalem Kalendertag summiert (Wert um 00:00 gehört zum Vortag); ESL-Werte werden nie aggregiert.

**Cache:** `_load` speichert die eingelesenen Daten als `.processed-v3.cache` im Datensatz. Der Cache wird neu gebaut, sobald sich eine XML-Datei oder eine `.py`-Datei des Pakets ändert.

Beispiel:

```bash
cd python
python -m volt_trace.cli sensors <VOLT_TRACE_DATA_DIR>/<UUID>
python -m volt_trace.cli export <VOLT_TRACE_DATA_DIR>/<UUID> ID742 zaehlerstand > ID742_zaehlerstand.csv
```

### Batch-Export (`volt_trace.main`)

Liest zwei Ordner (rekursiv) und schreibt pro Sensor `<Sensor>_verbrauch.csv` und, falls ESL vorhanden, `<Sensor>_zaehlerstand.csv` nach `--output-dir` (gleiches Format wie der Download):

```bash
cd python
python -m volt_trace.main --esl-dir pfad/zu/esl --sdat-dir pfad/zu/sdat --output-dir export
```

### Abgleich ESL vs. SDAT

`compare_esl_vs_sdat.py` vergleicht Differenzen zwischen ESL-Stichtagen und summierten SDAT-Volumina (lokales Hilfsskript, nicht Teil der Web-UI).

---

## Exportformate

Diese Beschreibung reicht, um den Export aus `main.py`, `cli.py` oder einer späteren API zu verwenden, ohne `export.py` zu lesen.

### Import

```python
from volt_trace.export import (
    KIND_CONSUMPTION, KIND_METER, DataPoint, consumption_points, meter_points,
    csv_filename, export_csv, export_json, to_csv_string, to_json_payload, to_json_string,
)
```

Aufbau wie in `sdat.py` und `esl.py`: ein Dataclass-Objekt für die Daten (`DataPoint`) und normale Funktionen für den Export.

### Eingabe: `DataPoint`

Ein Wert zu einem Zeitpunkt: Verbrauch eines Intervalls (Zeitpunkt = Intervallende) oder ESL-Zählerstand.

| Feld | Typ | Bedeutung |
|---|---|---|
| `time` | `datetime` **mit Zeitzone** (UTC) | Intervallende bzw. Ablesezeitpunkt |
| `value` | `float` | Verbrauch bzw. absoluter Zählerstand in kWh |

- Ein `datetime` **ohne** Zeitzone löst sofort `ValueError` aus. Die Zeitpunkte aus `sdat.py` und `esl.py` haben bereits UTC, sie können direkt übergeben werden.
- Die Funktionen für mehrere Sensoren erwarten die Daten als `Dict[str, List[DataPoint]]`: Sensorkennung → Liste von Zählerständen, z. B. `{"ID742": [...], "ID735": [...]}`.
- Die Sensorkennung darf nur `A-Z a-z 0-9 _ -` enthalten, sonst `ValueError`.
- Die Liste muss nicht sortiert sein, der Export sortiert selbst nach Zeit.
- Der Export aggregiert **nicht**. Für FA-10 („kleinstmöglicher Zeitabstand“) die 15-Minuten-Verbrauchswerte bzw. alle ESL-Stände übergeben, keine Tageswerte.

Umwandlung der eingelesenen Daten (zwei getrennte Quellen, keine Umrechnung):

| Funktion | Quelle | Ergebnis |
|---|---|---|
| `consumption_points(sdat_data)` | `load_sdat_folder` | `{sensor: [DataPoint(timestamp, volume)]}` für FA-10a |
| `meter_points(esl_data)` | `load_esl_folder` | `{sensor: [DataPoint(start_time, start_value)]}` für FA-10b |

### CSV (FA-10a / FA-10b)

| Funktion | Rückgabe | Zweck |
|---|---|---|
| `to_csv_string(points: List[DataPoint])` | `str` | CSV-Text **eines** Sensors; derselbe Text für Download (`cli export`) und Batch (`main.py`) |
| `csv_filename(sensor_id, kind)` | `str` | `ID742_verbrauch.csv` bzw. `ID742_zaehlerstand.csv` (`kind`: `KIND_CONSUMPTION` = `verbrauch`, `KIND_METER` = `zaehlerstand`) |
| `export_csv(data, target_folder, kind)` | `List[Path]` | schreibt pro Sensor eine Datei `csv_filename(sensor, kind)`, erstellt den Ordner falls nötig |

Format: Kopfzeile `timestamp,value`, Zeitstempel als Unix-Epoch in Sekunden (UTC), Wert mit 4 Nachkommastellen, Zeilenende `\n`.

```
timestamp,value
1503495302,82.0300
1503496202,82.0500
```

### JSON (FA-13, Vorbereitung FA-12)

| Funktion | Rückgabe | Zweck |
|---|---|---|
| `to_json_payload(data)` | `list` | Python-Liste im JSON-Format, z. B. als Body für den späteren HTTP POST (`requests.post(url, json=payload)`) |
| `to_json_string(data)` | `str` | JSON-Text, z. B. für einen Download |
| `export_json(data, target_file: Path)` | `Path` | schreibt **alle** Sensoren in **eine** Datei, erstellt den Ordner falls nötig |

Format gemäss Vorgabe des Auftraggebers: `ts` ist der Unix-Epoch als **String**, `value` der absolute Zählerstand (auf 4 Stellen gerundet). Sensoren sind nach Kennung sortiert.

```json
[
  {
    "sensorId": "ID735",
    "data": [ { "ts": "1503495302", "value": 1129336.0 } ]
  },
  {
    "sensorId": "ID742",
    "data": [ { "ts": "1503495302", "value": 82.03 } ]
  }
]
```

### Beispiel: vollständiger Export

```python
from pathlib import Path
from volt_trace.esl import load_esl_folder
from volt_trace.export import (KIND_CONSUMPTION, KIND_METER, consumption_points,
                               export_csv, export_json, meter_points)
from volt_trace.sdat import load_sdat_folder

sdat = load_sdat_folder(Path("daten/sdat"))
esl = load_esl_folder(Path("daten/esl"))

export_csv(consumption_points(sdat), Path("export"), KIND_CONSUMPTION)  # export/ID742_verbrauch.csv, …
export_csv(meter_points(esl), Path("export"), KIND_METER)               # export/ID742_zaehlerstand.csv, …
export_json(meter_points(esl), Path("export") / "meter_readings.json")  # optional, FA-13
```

`export_esl_comparison_csv` schreibt die Soll-Ist-Tabelle aus `analysis.compare_with_esl` (nur für `test_esl_vs_sdat.py`).

Die Ordner `python/export/` und `python/volt_trace/export/` sind im `.gitignore`.

---

## Tests

### Python

```bash
cd python
python -m pytest -q
```

| Datei | Inhalt |
|-------|--------|
| `tests/test_import_report.py` | Ordner- und ZIP-Import mit Unterordnern liefern dieselben Werte, gleichnamige Dateien bleiben erhalten, Metadaten, Importzahlen, unsichere/ungültige ZIPs, FA-06 bei gleicher `Creation` (relativer Pfad entscheidet), Faktor-3-Befund |
| `tests/test_sdat_timestamps.py` | FA-05: Intervallenden, 96/92/100/2976 Werte, `Unit`, Sequenzprüfung |
| `tests/test_daily_aggregation.py` | Tageswerte nach lokaler Mitternacht, Zeitumstellung |
| `tests/test_esl.py` | OBIS-Gruppierung, Hoch-/Niedertarif-Summe, UTC-Konvertierung, fehlende Register |
| `tests/test_cli_cache.py` | Cache von `_load` |
| `tests/test_quantities.py` | Rundung auf 4 Stellen (NFA-04) |
| `tests/test_analysis.py` | FA-07-Berechnung in `analysis.py` |
| `tests/test_esl_vs_sdat.py` | Soll-Ist-Vergleich am Beispieldatensatz; wird übersprungen, wenn `XML-Files/` fehlt. Der Toleranztest ist wegen des Faktor-3-Befunds `xfail` |
| `tests/fixtures/` | minimale ESL-XMLs |

Stand auf diesem Branch: **37 passed, 1 xfailed**.

### Frontend

```bash
npm --prefix nextjs ci        # einmalig, installiert u. a. tsx
npm --prefix nextjs test      # Session-Store, Diagramme, datetime (node:test via tsx)
```

Die Diagrammtests unter `nextjs/tests/charts/` prüfen Balken/Linie, Achsentitel, Europe/Zurich, Herbst-Doppelstunde und leere Reihen mit festen UTC-Fixtures.

---

## Beispieldaten

| Pfad | Inhalt |
|------|--------|
| `XML-Files/SDAT-Files/*.xml` | 5133 SDAT-Dateien; Sensoren ID742, ID735, ID26256, ID26257, ID26263 |
| `XML-Files/ESL-Files/*.xml` | 45 ESL-Dateien mit 44 verschiedenen Stichtagen je ID742/ID735 (Zähler `38157930`); Zähler `5442313` wird übergangen |

Der Ordner `XML-Files/` ist in `.gitignore` und muss lokal vorhanden sein. Ohne ihn werden die Tests mit Beispieldaten übersprungen.

Erwartete Exporte aus dem Beispieldatensatz (Zeilen ohne Kopfzeile): `ID742_verbrauch.csv` und `ID735_verbrauch.csv` je 129 116, `ID26256_verbrauch.csv` und `ID26257_verbrauch.csv` je 98 300, `ID26263_verbrauch.csv` 32, `ID742_zaehlerstand.csv` und `ID735_zaehlerstand.csv` je 44. Ordner- und ZIP-Import liefern identische CSV-Dateien.

---

## Funktionale Anforderungen (Übersicht)

Kurzstatus gegen die Seminar-Spezifikation (ohne Gewähr auf Vollständigkeit der Abnahme):

| ID | Thema | Status im Repo |
|----|--------|----------------|
| FA-01 | SDAT einlesen | Ordner und ZIP rekursiv, alle Felder inkl. `Creation`, Einheit und Status als `SdatSource`, Importbericht |
| FA-02 | ESL einlesen | `end`, OBIS, `value`, `factoryNo` und `status` als `EslSource`; Status ≠ `V` wird gemeldet |
| FA-03 | Sensoren / UI | alle Sensoren aus SDAT und ESL (Vereinigung), Mehrfachauswahl in der UI |
| FA-04 | OBIS-Summe HT+NT | Implementiert in `esl.py`; Zähler ohne Paare werden gemeldet |
| FA-05 | Zeitstempel aus Sequence | Intervallende, Einheit/Sequenz geprüft (`sdat.py`) |
| FA-06 | Duplikate nach Creation | neueste `Creation` gewinnt, bei Gleichstand der relative Pfad |
| FA-07 | Zählerstand aus SDAT | entfällt für Anzeige/Export; `analysis.py` nur noch für Befund und Tests |
| FA-08–09 | Verbrauchs- / Zählerstandsdiagramm | Recharts; Verbrauch aus SDAT, Zählerstand direkt aus ESL; mehrere Sensoren |
| FA-10 | CSV-Export | `_verbrauch.csv` für alle SDAT-Sensoren, `_zaehlerstand.csv` nur mit ESL (Download + `main.py`) |
| FA-11 | Klassen-/Komponentendiagramm | [`docs/architecture/`](docs/architecture/) |
| FA-12–13 | JSON HTTP POST / JSON-Datei | `to_json_payload` / `export_json` vorhanden; kein UI-Download, HTTP POST offen |

---

## Entwicklung

```bash
# Typecheck Frontend
npm --prefix nextjs run typecheck

# Produktionsbuild
npm --prefix nextjs run build
npm --prefix nextjs run start
```

Python-Abhängigkeiten: keine zur Laufzeit (nur Standardbibliothek); `requirements.txt` enthält `pytest` für die Tests.

### Wichtige Erweiterungspunkte

- Sichtbarer Upload-/Verarbeitungsfortschritt in Prozent (heute nur «Lade hoch …»)
- Hinweistext auf der Seite, wenn für einen Sensor keine ESL-Daten vorliegen (heute fehlt nur der Button)
- Objektorientierte Klassen für Einlesen, Aggregation und Export mit kompatiblen Wrappern (NFA-01)
- JSON-Download in der Oberfläche (FA-13) und HTTP-POST-Export (FA-12)

---

## Lizenz / Autoren

Seminarprojekt **volt-trace** — Version siehe `python/volt_trace/__init__.py` (`__version__`).
