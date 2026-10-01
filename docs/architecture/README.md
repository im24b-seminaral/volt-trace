# Architekturdiagramme (FA-11)

Kanoniche Mermaid-Quellen für das Abgabedatenmodell und die Laufzeitarchitektur von Volt Trace.

**Dokumentationsstand (Codeabgleich):** Git-Commit `387b998`  
**Pflichtenheft:** v1.0 (Gruppe 3, Energieagentur Bünzli)

## Dateien

| Datei | Inhalt |
|-------|--------|
| [`class-diagram.mmd`](class-diagram.mmd) | Python-`@dataclass`-Typen in `volt_trace` + Typalias `MeterSeries` |
| [`component-diagram.mmd`](component-diagram.mmd) | Browser, Next.js, temporäre Sitzungsdaten, Python-CLI als Unterprozess |

Ausführliche Erläuterung der Module: [`PYTHON.md`](../../PYTHON.md) (Kap. 4 und 9).

## Drei Datenströme (v1.0)

1. **SDAT-Verbrauch** — `MeasuredValue.volume`, Intervallende (FA-05); Web-Diagramm `consumption`, CSV `verbrauch` (FA-10a).
2. **ESL-Zählerstände** — echte Ablesungen `EslMeterReading`; Web-Diagramm `meter-reading`, CSV `zaehlerstand` (FA-10b).
3. **Berechnete Serie** — `MeterSeries` aus `analysis.calculate_all_meter_readings` für Verifikation (`compare_with_esl`, `main.py`, pytest); **nicht** die Quelle des Zählerstands-Diagramms in der Web-UI.

## Laufzeit (NFA-11 / NFA-12)

- Next.js bindet nur an **127.0.0.1**; Python öffnet **keinen** Netzwerkport (`execFile` auf `python -m volt_trace.cli`).
- Uploads und Cache liegen unter `VOLT_TRACE_DATA_DIR` (Default: OS-Temp); Zugriff nur mit gültigem Sitzungs-Cookie `vt_session` und registrierter Dataset-ID.
- Kein FastAPI-/uvicorn-Dienst in der Abgabe (dokumentierte Architekturentscheidung).

## Zuständigkeiten in der Parallelphase

| Issue | Schreibbereich |
|-------|----------------|
| #12 | Python-Quellcode, Tests, README, Upload/Export-Integration |
| #14 | `PYTHON.md`, `OFFENE_PUNKTE.md`, `docs/architecture/**` |
| #15 | `docs/acceptance/`, `tests/acceptance/` |

Endgültiger Diagramm-/Codeabgleich erfolgt am **integrierten Abgabecommit**, nicht durch parallele Edits derselben Quellfiles.

## Optionale Liefergegenstände (kein Muss in v1.0)

- **FA-12:** HTTP POST JSON an konfigurierbare URL (`export.py` / `requests`) — nicht in der Web-UI.
- **FA-13:** JSON-Download in der Oberfläche — `to_json_string` existiert; dediziertes CLI-Kommando optional (#12).
