# Architekturdiagramme (FA-11)

Kanoniche Mermaid-Quellen für das Abgabedatenmodell und die Laufzeitarchitektur von Volt Trace.

**Dokumentationsstand (Codeabgleich):** Git-Commit `0b776dd` (README); Diagrammdateien auf Stand `387b998`, siehe Hinweis unten  
**Pflichtenheft:** v1.0 (Gruppe 3, Energieagentur Bünzli)

## Dateien

| Datei | Inhalt |
|-------|--------|
| [`class-diagram.mmd`](class-diagram.mmd) | Python-`@dataclass`-Typen in `volt_trace` + Typalias `MeterSeries` |
| [`component-diagram.mmd`](component-diagram.mmd) | Browser, Next.js, temporäre Sitzungsdaten, Python-CLI als Unterprozess |

Ausführliche Erläuterung der Module: [`PYTHON.md`](../../PYTHON.md) (Kap. 4 und 9).

> **Hinweis – noch nicht in den `.mmd`-Dateien:** Seit PR #16 gibt es zusätzlich `SdatSource`, `SdatDataset` (`sdat.py`) sowie `EslSource`, `EslValueRow`, `EslDataset` (`esl.py`); `MeasuredValue` und `EslMeterReading` haben ein Feld `source`. Im Komponentendiagramm fehlen der ZIP-/Ordnerimport mit `import-report.json` und die Komponenten `ImportReport` und `ChartFilters`. Die aktuelle Klassenübersicht steht in `PYTHON.md` Kap. 4.

## Drei Datenströme (v1.0)

1. **SDAT-Verbrauch** — `MeasuredValue.volume`, Intervallende (FA-05); Web-Diagramm `consumption`, CSV `verbrauch` (FA-10a) für alle SDAT-Sensoren.
2. **ESL-Zählerstände** — echte Ablesungen `EslMeterReading`; Web-Diagramm `meter-reading`, CSV `zaehlerstand` (FA-10b) nur für Sensoren mit ESL.
3. **Berechnete Serie** — `MeterSeries` aus `analysis.calculate_all_meter_readings` nur für den Faktor-3-Befund im Importbericht und für Tests (`compare_with_esl`); **nicht** die Quelle des Zählerstands-Diagramms und nicht von `main.py` verwendet.

## Import (FA-01 / FA-02 / NFA-06)

- Upload von XML- und ZIP-Dateien oder einem Ordner; Next.js speichert die Dateien mit relativem Pfad, `cli sort-files` entpackt ZIPs sicher und verschiebt rekursiv nach `sdat/` / `esl/`.
- Der Importbericht (gefunden, eingelesen, übersprungen, Datensatz-Skips, Gründe, Befunde) wird als `import-report.json` im Datensatz gespeichert und auf der Seite angezeigt.

## Laufzeit (NFA-11 / NFA-12)

- Next.js bindet nur an **127.0.0.1**; Python öffnet **keinen** Netzwerkport (`execFile` auf `python -m volt_trace.cli`, Timeout 180 s).
- Uploads, `import-report.json` und Cache (`.processed-v3.cache`) liegen unter `VOLT_TRACE_DATA_DIR` (Default: OS-Temp); Zugriff nur mit gültigem Sitzungs-Cookie `vt_session` und registrierter Dataset-ID.
- Kein FastAPI-/uvicorn-Dienst in der Abgabe (dokumentierte Architekturentscheidung).

## Zuständigkeiten in der Parallelphase

| Issue | Schreibbereich |
|-------|----------------|
| #11 | Diagrammkomponenten, `ChartForm`, `datetime.ts`, UI-Chart-Helfer, `nextjs/tests/charts/` |
| #12 | Python-Quellcode und -Tests, Upload/Seite/Download, `python.ts`, `types.ts`, README |
| #14 | `PYTHON.md`, `OFFENE_PUNKTE.md`, `docs/architecture/**` |
| #15 | `docs/acceptance/`, `tests/acceptance/`, `scripts/acceptance/` |

Endgültiger Diagramm-/Codeabgleich erfolgt am **integrierten Abgabecommit**, nicht durch parallele Edits derselben Quellfiles.

## Optionale Liefergegenstände (kein Muss in v1.0)

- **FA-12:** HTTP POST JSON an konfigurierbare URL (`export.py` / `requests`) — nicht in der Web-UI.
- **FA-13:** JSON-Download in der Oberfläche — `to_json_string` existiert; dediziertes CLI-Kommando optional (#12).
