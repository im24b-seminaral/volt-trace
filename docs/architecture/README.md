# Architekturdiagramme (FA-11)

Kanonische Mermaid-Quellen für das Abgabedatenmodell und die Laufzeitarchitektur von Volt Trace.

**Codeabgleich:** integrierter lokaler Stand `3dcd2d49f1beeecf86fdf2049a4345898d8f35db` (01.10.2026); das Diagramm ist eine noch nicht commitete Dokumentationsänderung auf diesem Stand.
**Pflichtenheft:** v1.0 (Gruppe 3, Energieagentur Bünzli)

## Dateien

| Datei | Inhalt |
|-------|--------|
| [`class-diagram.mmd`](class-diagram.mmd) | Alle 13 Python-Klassen in `volt_trace` mit Quellenbeziehungen; `MeterSeries` ist ausdrücklich nur ein Typalias |
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

Für den obigen integrierten Stand wurden alle Klassendefinitionen in `python/volt_trace/*.py` mit dem Diagramm abgeglichen. Bei späteren Codeänderungen muss dieser Abgleich erneut erfolgen.

## Optionale Liefergegenstände (kein Muss in v1.0)

- **FA-12 (geplant, nicht implementiert):** HTTP POST JSON an eine konfigurierbare URL. Es gibt dafür keine Klasse im Diagramm; `export.py` kann JSON erzeugen und in eine Datei schreiben.
- **FA-13 (geplant, nicht implementiert):** JSON-Download in der Oberfläche. `to_json_string` existiert, ein UI-Download dafür noch nicht.
