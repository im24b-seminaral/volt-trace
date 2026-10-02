# Volt Trace

Webanwendung zur Auswertung von Schweizer Stromzählerdaten. Sie liest XML-Dateien im **SDAT**- und **ESL**-Format ein, zeigt Verbrauch und Zählerstände als Diagramm und exportiert sie als CSV oder JSON.

| Format | Was steht drin? | Beispiel |
|--------|-----------------|----------|
| **SDAT** | Verbrauch pro 15 Minuten (relativ) | Kassenzettel: «heute 12 Fr. ausgegeben» |
| **ESL** | Zählerstand an einem Stichtag (absolut) | Kontoauszug: «Kontostand 1250 Fr.» |

Zwei Sensoren sind benannt: **ID742** = Netzbezug, **ID735** = Einspeisung (z. B. Solar). Weitere Sensor-IDs aus den Dateien werden ebenfalls angezeigt.

Details zum Python-Code: [PYTHON.md](PYTHON.md). Abnahmeunterlagen: [docs/acceptance/](docs/acceptance/).

---

## Aufbau

```text
Browser ──► Next.js (nextjs/, Port 3000, nur 127.0.0.1)
                │  startet pro Anfrage: python -m volt_trace.cli …
                ▼
            Python (python/volt_trace/)  — kein eigener Netzwerkport
            sdat.py · esl.py · analysis.py · export.py · cli.py
```

Hochgeladene Dateien liegen **nur zur Laufzeit** im Datenverzeichnis (`VOLT_TRACE_DATA_DIR`, sonst OS-Temp-Ordner `volt-trace-data/<UUID>/`), nie im Repository.

---

## Voraussetzungen

- **Python 3.14+**
- **Node.js 24.x** (ältere Versionen melden `EBADENGINE` bei `npm ci`)
- Windows, macOS oder Linux

## Installation

Im Repository-Root:

```bash
python3 -m venv python/.venv                              # Windows: python -m venv python\.venv
./python/.venv/bin/pip install -r python/requirements.txt
./python/.venv/bin/pip install -e python
npm --prefix nextjs ci
```

Unter Windows liegt das venv-Python in `python\.venv\Scripts\python`.

## Starten

```bash
npm --prefix nextjs run dev     # Produktion: npm --prefix nextjs run build && npm --prefix nextjs run start
```

Dann [http://127.0.0.1:3000](http://127.0.0.1:3000) öffnen. Next.js nutzt automatisch `python/.venv`, sonst `python`/`python3` aus dem PATH.

---

## Bedienung

1. **XML- oder ZIP-Dateien hochladen** (Ordner inklusive Unterordnern möglich). Der Importbericht zeigt, was eingelesen und was übersprungen wurde.
2. **Diagramm wählen:**
   - **Verbrauch** — SDAT-Werte, Auflösung Tag oder 15 Minuten.
   - **Zählerstand** — die abgelesenen ESL-Stichtagswerte (nicht aggregiert).
3. **Sensoren** ankreuzen (mehrere gleichzeitig) und **Zeitraum** wählen.
4. **Export** pro Sensor als CSV oder JSON herunterladen oder per **HTTP POST** an eine selbst eingegebene Zieladresse senden.

**Zeitzone:** intern und im Export immer **UTC**; Diagramm, Tooltips und die Datumsfilter zeigen **Europe/Zurich**.

### Sitzung und Datenschutz

- Keine Benutzerkonten. Die Zuordnung läuft über das HttpOnly-Cookie `vt_session`.
- Ein fremder `?dataset=<UUID>`-Link nützt nichts: Diagramm und Export prüfen die Eigentümerschaft (sonst HTTP 403).
- **„Sitzung beenden“** löscht Dateien und Cache sofort. Sonst endet die Sitzung nach ca. 2 Minuten Inaktivität (`SESSION_IDLE_TTL_MS`); ein Timer räumt alle 30 Sekunden ab, zusätzlich beim Serverstart.

---

## Python-CLI

Die Web-Oberfläche ruft diese Kommandos auf; sie lassen sich auch direkt nutzen (aus dem Ordner `python/`):

| Kommando | Argumente | Ausgabe |
|----------|-----------|---------|
| `sort-files` | `<quellDir> <datensatzDir>` | sortiert XML nach `sdat/` und `esl/`, JSON-Importbericht |
| `sensors` | `<datensatzDir>` | JSON: Sensorliste mit `hasConsumption` / `hasMeterReadings` |
| `series` | `<datensatzDir> <sensorId> <kind> <resolution> <von> <bis>` | JSON-Zeitreihe (`kind`: `consumption`\|`meter-reading`, `resolution`: `day`\|`15min`) |
| `export` | `<datensatzDir> <sensorId> <kind> [csv\|json]` | Export auf stdout (`kind`: `verbrauch`\|`zaehlerstand`) |

```bash
cd python
python -m volt_trace.cli export /pfad/zum/datensatz ID742 verbrauch csv
```

Batch-Pipeline ohne Web-UI — schreibt je eine CSV pro Sensor und Art:

```bash
python -m volt_trace.main --sdat-dir pfad/sdat --esl-dir pfad/esl --output-dir export
```

## Exportformate

**CSV** — Kopfzeile, Unix-Zeitstempel in Sekunden (UTC), Wert in kWh mit 4 Nachkommastellen:

```csv
timestamp,value
1503495302,82.0300
```

**JSON** — Zeitstempel als String, Sensoren nach Kennung sortiert:

```json
[ { "sensorId": "ID742", "data": [ { "ts": "1503495302", "value": 82.03 } ] } ]
```

## Tests

```bash
cd python && python -m pytest -q      # Python: Parser, Zeitstempel, Aggregation, Export, Import-Bericht
npm --prefix nextjs run test          # Frontend: Session-Store, Diagrammfilter
npm --prefix nextjs run typecheck
```

Prüfplan und Testprotokoll der Abnahme: [docs/acceptance/](docs/acceptance/).

---

## Projektstruktur

```text
volt-trace/
├── nextjs/              Next.js 16 Frontend
│   └── src/
│       ├── app/         Seite, Upload, Download- und HTTP-POST-Route
│       ├── components/  Diagramme, Upload, Filter (shadcn/ui)
│       └── lib/         python.ts (Subprozess), session.ts, datetime.ts
├── python/
│   ├── volt_trace/      sdat.py · esl.py · analysis.py · export.py · cli.py · main.py
│   └── tests/           pytest
├── docs/acceptance/     Prüfplan, Testprotokoll, Nachweise
├── scripts/ · tests/    Werkzeuge und Fixtures für die Abnahme
├── PYTHON.md            Erklärung des Python-Teils
└── README.md
```

---

Seminarprojekt **volt-trace** v1.0 — Version im Code: `python/volt_trace/__init__.py`.
