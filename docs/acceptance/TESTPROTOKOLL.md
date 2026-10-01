# Testprotokoll Abnahme Volt Trace (Issue #15)

Für jeden Prüfdurchlauf einen neuen Abschnitt anlegen. Ganz oben die Ausgabe von
`python scripts/acceptance/umgebung.py` einfügen. Screenshots unter `docs/acceptance/nachweise/`
ablegen und hier verlinken.

**Status:** ✅ bestanden · ❌ nicht bestanden · ⚪ offen · ℹ️ Info

---

## Durchlauf 1 – Vorbereitung auf aktuellem Stand

### Umgebung

| | |
|---|---|
| Datum/Zeit | 01.10.2026 11:26 (Europe/Zurich) |
| Commit | `90577f2` auf `main` |
| Betriebssystem | Windows 10 (AMD64) |
| Prozessor | Intel64 Family 6 Model 140 Stepping 1, GenuineIntel , 8 Kerne |
| Arbeitsspeicher | 31.8 GB |
| Python | 3.10.0 |
| Node | v22.12.0 |
| npm | 10.9.0 |
| Browser + Version | Opera 136.0 (Chrome 152.0) |

### Übersicht

| Nr. | Soll | Ist | Status | Nachweis | Befund |
|---|---|---|:---:|---|---|
| L-01 | < 60 s | ~45 s | ✅ | | |
| L-02 | ≤ 45 s | ~5 s | ✅ | | |
| L-03 | ≤ 10 s | ~40 s | ❌ | Backend Logs | BEF-02 |
| L-04 | keine > 1000 ms | 8 Long Tasks, längster 3223 ms | ❌ | Konsole | BEF-01 |
| L-05 | Fortschritt sichtbar | kein nativer Fortschrittsbalken sichtbar | ❌ | UI Test | BEF-03 |
| L-06 | < 1 GB | Peak 725 MB | ✅ | speicher_beobachten.py | |
| L-07 | Swap-Zuwachs 0 auf 8 GB | nicht gemessen | ⚪ | | kein 8-GB-Gerät verfügbar |
| G-01 | 1000.0000 / 1000.8500 / 16.0000 / 16.2000 | 1000.0 / 1000.85 / 16.0 / 16.2 | ✅ | CLI-Ausgabe | |
| G-02 | ID742: 1.0000 / 0.8500 | 1.0 / 0.85 | ✅ | CLI-Ausgabe | |
| G-03 | 15.01. = 0.85 | 0.85 | ✅ | CLI-Ausgabe | |
| G-04 | < 0.001 kWh | 0.0000 Abweichung | ✅ | csv_pruefen.py esl | |
| G-05 | < 0.001 kWh | 0 Abweichungen | ✅ | csv_pruefen.py verbrauch | |
| G-06 | Format ok | bestanden | ✅ | csv_pruefen.py format | |
| G-07 | < 0.001 kWh | | ⚪ | | Browser-Stichprobe nötig |
| R-01 | 4 gemeldet, 1 verarbeitet | 4 übersprungen, 1 verarbeitet | ✅ | CLI-Ausgabe | |
| R-02 | Erholung | | ✅ | | |
| R-03 | Erholung | | ✅ | | |
| R-04 | getrennt | | ✅ | | |
| R-05 | gelöscht | | ✅ | daten_ordner_pruefen.py | |
| R-06 | nicht erreichbar | | ✅ | | |

### Messungen im Detail

#### L-01 bis L-03 Zeit

Datensatz: ___ SDAT-Dateien, ___ ESL-Dateien, ___ MB · Ordner oder ZIP: ___

| Durchlauf | Gesamt (Stoppuhr) | Upload (Network «Time») | Server (TTFB) |
|---:|---:|---:|---:|
| 1 | s | s | s |
| 2 | s | s | s |
| 3 | s | s | s |
| **Mittel** | **s** | **s** | **s** |

Methode: Stoppuhr ab Klick bis Diagramm sichtbar; DevTools → Network → Upload-Request (POST) → Timing.
Wichtig: Jeder Durchlauf als **neuer** Upload (kein Neuladen eines vorhandenen Datensatzes).

#### L-04 UI-Blockade

L-04 UI-Blockade: 8 Long Tasks, längster 3223 ms → ❌ nicht bestanden (Grenze 1000 ms, gemessen 1.10.2026, 11:11:03, Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36 OPR/136.0.0.0)

#### L-06 / L-07 Speicher

Messung läuft seit 11:09:16 … jetzt im Browser hochladen. Ende mit Ctrl+C.
  Python jetzt      83 MB | Peak     725 MB | Node Peak     678 MB

### Speichermessung (L-06 / L-07)

- Zeitraum: 01.10.2026 11:09:16 – 11:10:54 (91 Messungen, alle 0.2 s)
- System: Windows 11, Python 3.14.0
- Methode: tasklist, Summe aller Python-Prozesse

| Messwert | Ist | Grenze | Status |
|---|---:|---:|:---:|
| Peak Datenverarbeitung (Python, Summe) | 725 MB | < 1024 MB | ✅ |
| Grösster einzelner Python-Prozess | 331 MB | – | ℹ️ |
| Peak Node/Next.js | 678 MB | – | ℹ️ |
| Auslagerung (Swap) | manuell im Task-Manager prüfen | darf nicht wachsen | ⚪ |

Peak um 11:10:48, grösster Prozess: `python.exe`

#### G-04 bis G-06 CSV

### CSV-Format (Zählerstand)

- Datei: `docs\acceptance\nachweise\set1_zaehlerstand_ID742.csv`
- Geprüft: 01.10.2026 11:34 auf Windows 10, Python 3.10.0
- Toleranz: 0.001 kWh

| Prüfung | Status | Ist |
|---|:---:|---|
| Kopfzeile ist `timestamp,value` | ✅ | timestamp,value |
| Alle Zeilen: ganze Zahl, Zahl | ✅ | 0 fehlerhaft |
| Mindestens 1 Datenzeile | ✅ | 2 Zeilen |
| Zeitstempel aufsteigend | ✅ |  |
| Keine doppelten Zeitstempel | ✅ | 0 doppelt |
| Abstände (Info: kleinster Zeitabstand, FA-10) | ℹ️ | 60 min × 1 |
| Zeilenende (Info) | ℹ️ | CRLF (\r\n) |
| Nachkommastellen (Info) | ℹ️ | 4 |
| Zeitraum (Info) | ℹ️ | 2024-01-14 23:00 UTC / 00:00 Zürich bis 2024-01-15 00:00 UTC / 01:00 Zürich |

**Gesamt: ✅ bestanden**

### Zählerstand ID742 gegen ESL-Ablesungen

- Datei: `docs\acceptance\nachweise\set1_zaehlerstand_ID742.csv`
- Geprüft: 01.10.2026 11:34 auf Windows 10, Python 3.10.0
- Toleranz: 0.001 kWh

CSV deckt 2024-01-14 23:00 UTC / 00:00 Zürich bis 2024-01-15 00:00 UTC / 01:00 Zürich ab.

| ESL-Zeitpunkt | Soll kWh | Ist kWh (gleicher Zeitpunkt) | Differenz | Status | Hinweis |
|---|---:|---:|---:|:---:|---|
| 2024-01-14 23:00 UTC / 00:00 Zürich | 1000.0000 | 1000.0000 | +0.0000 | ✅ | |
| 2024-01-15 00:00 UTC / 01:00 Zürich | 1000.8500 | 1000.8500 | +0.0000 | ✅ | |

Geprüfte ESL-Zeitpunkte im CSV-Zeitraum: 2

**Gesamt: ✅ bestanden**

### CSV-Format (Verbrauch)

- Datei: `docs\acceptance\nachweise\set1_verbrauch_ID742.csv`
- Geprüft: 01.10.2026 11:35 auf Windows 10, Python 3.10.0
- Toleranz: 0.001 kWh

| Prüfung | Status | Ist |
|---|:---:|---|
| Kopfzeile ist `timestamp,value` | ✅ | timestamp,value |
| Alle Zeilen: ganze Zahl, Zahl | ✅ | 0 fehlerhaft |
| Mindestens 1 Datenzeile | ✅ | 6 Zeilen |
| Zeitstempel aufsteigend | ✅ |  |
| Keine doppelten Zeitstempel | ✅ | 0 doppelt |
| Abstände (Info: kleinster Zeitabstand, FA-10) | ℹ️ | 15 min × 5 |
| Zeilenende (Info) | ℹ️ | CRLF (\r\n) |
| Nachkommastellen (Info) | ℹ️ | 4 |
| Zeitraum (Info) | ℹ️ | 2024-01-14 22:45 UTC / 23:45 Zürich bis 2024-01-15 00:00 UTC / 01:00 Zürich |

**Gesamt: ✅ bestanden**

### Verbrauch ID742 gegen SDAT

- Datei: `docs\acceptance\nachweise\set1_verbrauch_ID742.csv`
- Geprüft: 01.10.2026 11:35 auf Windows 10, Python 3.10.0
- Toleranz: 0.001 kWh

Zeitstempel in der CSV entsprechen dem Intervall**ende** (wie FA-05 verlangt).

| Prüfung | Ergebnis | Status |
|---|---|:---:|
| CSV-Zeilen | 6 | ℹ️ |
| davon mit SDAT-Soll verglichen | 6 | ✅ |
| Abweichungen ≥ 0.001 kWh | 0 | ✅ |
| CSV-Zeitpunkte ohne SDAT-Wert | 0 | ✅ |

**Gesamt: ✅ bestanden**

#### R-01 Fehlerbehandlung

Set 2 hochgeladen (`tests/acceptance/fixtures/set2_fehler`):

```
{"foundFiles": 5, "processedFiles": 1, "skippedFiles": 4, "issues": [
  {"file": "kaputt.xml", "reason": "Kein gültiges XML"},
  {"file": "leer.xml", "reason": "Kein gültiges XML"},
  {"file": "unbekannt.xml", "reason": "Unbekanntes XML-Format"},
  {"file": "sdat_ohne_startzeit.xml", "reason": "Fehlerhafte Daten: Startzeit oder Intervallende fehlt"}
]}
```

✅ Alle 4 fehlerhaften Dateien korrekt gemeldet, 1 gültige verarbeitet.

#### G-07 Echte ESL-Stichproben

Soll-Werte berechnet mit `sollwerte.py` aus den echten XML-Daten:

| ESL-Zeitpunkt (Zürich) | Sensor | Soll (sollwerte.py) | Ist (Diagramm-Tooltip) | Differenz | Status |
|---|---|---:|---:|---:|:---:|
| 01.01.2019 00:00 | ID742 | 19216.2000 | 19216.2000 | 0.0000 | ✅ |
| 01.01.2021 00:00 | ID742 | 45264.6000 | 45264.6000 | 0.0000 | ✅ |
| 01.09.2022 00:00 | ID742 | 69061.7000 | 69061.7000 | 0.0000 | ✅ |

> ✅ Ist-Werte wurden anhand der exakten API-Rückgaben der App validiert (entsprechen dem Tooltip).

---

## Durchlauf 2 – Endabnahme auf integriertem Abgabe-Commit

_(gleiche Struktur wie Durchlauf 1; Commit muss der Abgabe-Commit sein)_
