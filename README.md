# Volt Trace

Webanwendung und Python-Paket zur Auswertung von Schweizer Stromzählerdaten im **SDAT**-Format (relative 15-Minuten-Verbräuche) und **ESL**-Format (absolute Zählerstände an Stichtagen). Dateien werden lokal eingelesen, als Diagramm angezeigt und als CSV exportiert.

| Sensor-ID | Bedeutung | Richtung |
|-----------|-----------|----------|
| **ID742** | Netzbezug | Netz → Gebäude |
| **ID735** | Einspeisung (z. B. Solar) | Gebäude → Netz |

**Weitere Dokumentation**

- [`PYTHON.md`](PYTHON.md) — Python-Paket im Detail (Parser, Datenklassen, Export-API)
- [`docs/architecture/`](docs/architecture/) — Klassen- und Komponentendiagramm (FA-11)
- [`docs/acceptance/`](docs/acceptance/) — Prüfplan und Testprotokolle
- [`docs/ABNAHME_RUNTIME_v1.0.md`](docs/ABNAHME_RUNTIME_v1.0.md) — Plattformnachweise Python/Node

---

## Voraussetzungen

| Komponente | Version |
|------------|---------|
| **Python** | **3.14+** ([`python/.python-version`](python/.python-version)) |
| **Node.js** | **24.x LTS** ([`nextjs/package.json`](nextjs/package.json) `engines`) |

Plattformen: Windows / macOS / Linux. Node 22 oder älter löst bei `npm ci` eine `EBADENGINE`-Warnung aus; für die Abnahme ist Node 24 vorgeschrieben. Zur Laufzeit braucht `volt_trace` nur die Python-Standardbibliothek; `requirements.txt` enthält `pytest` für die Tests.

## Installation

Im Repository-Root (enthält `python/` und `nextjs/`):

```bash
# macOS / Linux
python3 -m venv python/.venv
./python/.venv/bin/pip install -r python/requirements.txt
./python/.venv/bin/pip install -e python
npm --prefix nextjs ci
```

```powershell
# Windows (PowerShell)
python -m venv python\.venv
.\python\.venv\Scripts\python -m pip install -r python\requirements.txt
.\python\.venv\Scripts\python -m pip install -e python
npm --prefix nextjs ci
```

---

## Web-Oberfläche

```bash
npm --prefix nextjs run dev     # http://127.0.0.1:3000
```

Dev- und Produktionsstart binden nur an **127.0.0.1** (kein LAN-Zugriff). Next.js verwendet automatisch `python/.venv`, sonst `python`/`python3` aus dem PATH.

### Bedienung

1. **XML-/ZIP-Dateien oder einen Ordner wählen** (inklusive Unterordner). Der Upload meldet den Fortschritt laufend zurück; das Zeitbudget der Python-Verarbeitung ist 90 s.
2. Danach erscheint der **Importbericht** als eigene Seite (`/import/<datasetId>`): gefundene, eingelesene und übersprungene Dateien, Sensoren mit Zeitraum sowie Befunde (kaputte ZIP/XML, Duplikate, Zeitumstellung, ESL-/SDAT-Abweichungen). Gültige Dateien werden trotz Fehlern weiter verarbeitet.
3. In der Auswertung **Sensor(en)**, **Zeitraum** (Kalendertage in Europe/Zurich, Kürzel „7 Tage / Monat / Jahr / Alles“) und **Diagrammtyp** wählen:
   - **Verbrauch** — SDAT-`Volume`, in der Tagesansicht Summe pro Kalendertag.
   - **Zählerstand** — ESL-Ablesungen an den Stichtagen.
   Die **Auflösung ergibt sich aus dem Zeitraum**: bis 7 Tage 15 Minuten, darüber Tageswerte.
4. **CSV exportieren** — pro Sensor „Verbrauch (CSV)“ und „Zählerstände (CSV)“.

Auswählbar sind nur Sensoren, für die **sowohl SDAT- als auch ESL-Daten** vorliegen.

### Zeitzone

- Diagrammachse und Tooltips zeigen Europe/Zurich (`DD.MM.YYYY` bzw. `DD.MM.YYYY HH:mm`), Umrechnung in [`nextjs/src/lib/datetime.ts`](nextjs/src/lib/datetime.ts).
- CLI/JSON liefern UTC-ISO-Strings, der CSV-Export Unix-Zeitstempel in UTC.

### Sitzung und Datenschutz (NFA-11 / NFA-12)

- Keine Konten: Zugriff über das HttpOnly-Session-Cookie `vt_session`.
- `?dataset=<UUID>` allein genügt nicht — Diagramm und Export prüfen, ob die UUID zur Sitzung gehört (fremde IDs → Fehlermeldung bzw. HTTP 403).
- Hochgeladene Daten liegen **nur zur Laufzeit** unter `<Datenverzeichnis>/<UUID>/` mit `sdat/`, `esl/` und `.processed-v3.cache`, nie im Repository.
- Fehlgeschlagene Uploads löschen ihren Ordner; abgelaufene Sitzungen werden beim nächsten Request samt Daten und Cache bereinigt.

| Umgebungsvariable | Standard | Wirkung |
|---|---|---|
| `VOLT_TRACE_DATA_DIR` | OS-Temp `volt-trace-data/` | Ablage der Laufzeitdaten |
| `SESSION_IDLE_TTL_MS` | `14400000` (4 h) | Idle-Zeit bis zum Aufräumen einer Sitzung |

---

## Architektur

```text
Next.js (nextjs/, Port 3000, nur 127.0.0.1)
  Upload-Route (NDJSON-Fortschritt) · Seite mit Diagrammen · CSV-Download-Route
        │  exec: python -m volt_trace.cli …   (venv: python/.venv)
        ▼
Python (python/volt_trace/)
  sdat.py · esl.py · analysis.py · report.py · export.py
  cli.py   Schnittstelle für die Web-UI
  main.py  Batch-Pipeline (Ordner → CSV)
```

Kein Python-HTTP-Server und kein offener Port in Python: Next.js startet Subprozesse ([`nextjs/src/lib/python.ts`](nextjs/src/lib/python.ts)).

## Datenformate

**SDAT** (`ValidatedMeteredData`): `DocumentID` liefert die Sensor-ID (Suffix nach `_`), `Interval`/`Resolution` den Zeitraster, `Observation` die `Sequence` samt `Volume` (kWh).
Zeitstempel = `StartDateTime + Sequence × Resolution` → **Intervallende in UTC** (FA-05). Bei gleichem Zeitstempel aus mehreren Dateien gewinnt die zuletzt erstellte Datei (`Creation`).

**ESL** (`ESLBillingData`): `TimePeriod end` ist der Ablesezeitpunkt in **Lokalzeit Europe/Zurich** und wird nach UTC konvertiert. Der Zählerstand ist die Summe aus Hoch- und Niedertarif, **nur** wenn beide Register vorhanden sind:

| Richtung | Hochtarif | Niedertarif | Sensor |
|----------|-----------|-------------|--------|
| Bezug | `1-1:1.8.1` | `1-1:1.8.2` | ID742 |
| Einspeisung | `1-1:2.8.1` | `1-1:2.8.2` | ID735 |

Andere OBIS-Gruppen (z. B. `1-1:1.8.0`) werden ignoriert, doppelte Stichtage pro Sensor entfernt.

### Bekannte Einschränkung

`analysis.py` kann aus einem ESL-Anker und den SDAT-Volumen eine fortlaufende Zählerstandskurve rechnen (vorwärts und rückwärts, Abgleich mit Toleranz 0,001 kWh). **Diagramm und CSV-Export zeigen diese berechnete Kurve nicht**, sondern die ESL-Ablesungen: im Beispieldatensatz weicht die Summe der SDAT-Volumen zwischen zwei Stichtagen um etwa Faktor 3 von der ESL-Differenz ab. Diese Abweichung ist offen und wird bewusst nicht im Code „korrigiert“.

---

## Python-CLI

Aufruf aus dem Ordner `python/` (venv aktiv oder `python -m`):

| Kommando | Argumente | Ausgabe |
|----------|-----------|---------|
| `sort-files` | `<srcDir> <datasetDir>` | JSON; entpackt ZIPs und sortiert Dateien nach `sdat/` / `esl/` |
| `sensors` | `<datasetDir>` | JSON: Sensoren mit `hasConsumption`, `hasMeterReadings`, Datumsbereich |
| `series` | `<datasetDir> <sensorId> <kind> <resolution> <from> <to>` | JSON-Zeitreihe; `kind`: `consumption` \| `meter-reading`, `resolution`: `day` \| `15min` |
| `export` | `<datasetDir> <sensorId> <kind>` | CSV auf stdout; `kind`: `verbrauch` \| `zaehlerstand` |

```bash
cd python
python -m volt_trace.cli sensors <VOLT_TRACE_DATA_DIR>/<UUID>
python -m volt_trace.cli export  <VOLT_TRACE_DATA_DIR>/<UUID> ID742 verbrauch > ID742.csv
```

Mit `VOLT_TRACE_PROGRESS=1` schreibt die CLI zusätzlich `@progress …`-Zeilen auf stdout (nutzt die Web-UI).

### Batch-Pipeline

Liest beide Ordner und schreibt pro Sensor je eine CSV-Datei (Verbrauch und ESL-Zählerstand) nach `--output-dir`:

```bash
cd python
python -m volt_trace.main --esl-dir pfad/zu/esl --sdat-dir pfad/zu/sdat --output-dir export
```

`compare_esl_vs_sdat.py` und `calc_values.py` sind lokale Hilfsskripte für den Abgleich bzw. Kennzahlen, nicht Teil der Web-UI.

### CSV-Format (FA-10)

Kopfzeile `timestamp,value`, Zeitstempel als Unix-Epoch in Sekunden (UTC), Wert mit 4 Nachkommastellen, Zeilenende `\n`. Dateiname beim Datei-Export: `<Sensor>_<verbrauch|zaehlerstand>.csv`.

```
timestamp,value
1503495302,82.0300
1503496202,82.0500
```

JSON (`to_json_string`, `export_json`) ist im Paket vorhanden, aber nicht in der UI verdrahtet. Signaturen und Datenklassen: [`PYTHON.md`](PYTHON.md).

---

## Tests und Entwicklung

```bash
cd python && python -m pytest -q        # Parser, Zeitstempel, Aggregation, Importbericht
npm --prefix nextjs test                # Session-Store, Diagramme, Datums-Helfer
npm --prefix nextjs run typecheck
npm --prefix nextjs run build && npm --prefix nextjs run start
```

Beispieldaten für End-to-End-Durchläufe: `tests/set1_normal/` (gültiger Satz inkl. ZIP), `tests/set2_fehler/` (kaputte und leere Dateien), `python/tests/fixtures/` (minimale ESL-/SDAT-XMLs). Für eigene Datensätze SDAT- und ESL-Ordner mit gleichen Sensor-IDs und überlappendem Zeitraum verwenden.

---

Seminarprojekt **volt-trace** — Version siehe `python/volt_trace/__init__.py` (`__version__`).
