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
| Datum/Zeit | 01.10.2026 10:16 (Europe/Zurich) |
| Commit | `ea21ddf` auf `issue-15-abnahme` |
| Betriebssystem | Windows 11 (AMD64) |
| Prozessor | Intel64 Family 6 Model 140 Stepping 1, GenuineIntel , 8 Kerne |
| Arbeitsspeicher | 31.8 GB |
| Python | 3.14.0 |
| Node | v22.12.0 |
| npm | 10.9.0 |
| Browser + Version | _(von Hand eintragen, z. B. Chrome 141.0)_ |

### Übersicht

| Nr. | Soll | Ist | Status | Nachweis | Befund |
|---|---|---|:---:|---|---|
| L-01 | < 60 s | | ⚪ | | |
| L-02 | ≤ 45 s | | ⚪ | | |
| L-03 | ≤ 10 s | | ⚪ | | |
| L-04 | keine > 1000 ms | | ⚪ | | |
| L-05 | Fortschritt sichtbar | | ⚪ | | |
| L-06 | < 1 GB | | ⚪ | | |
| L-07 | Swap-Zuwachs 0 auf 8 GB | | ⚪ | | |
| G-01 | 1000.0000 / 1000.8500 / 16.0000 / 16.2000 | | ✅ | | |
| G-02 | ID742: 1.0000 / 0.8500 | | ✅ | | |
| G-03 | 15.01. = 0.85 | | ✅ | | |
| G-04 | < 0.001 kWh | | ✅ | | |
| G-05 | < 0.001 kWh | | ✅ | | |
| G-06 | Format ok | | ✅ | | |
| G-07 | < 0.001 kWh | | ⚪ | | |
| R-01 | 4 gemeldet, 1 verarbeitet | | ✅ | | |
| R-02 | Erholung | | ⚪ | | |
| R-03 | Erholung | | ⚪ | | |
| R-04 | getrennt | | ⚪ | | |
| R-05 | gelöscht | | ⚪ | | |
| R-06 | nicht erreichbar | | ⚪ | | |

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

_(Ausgabe von `abnahmeErgebnis()` einfügen)_

#### L-06 / L-07 Speicher

_(Ausgabe von `speicher_beobachten.py` einfügen)_

#### G-04 bis G-06 CSV

### CSV-Format

- Datei: `docs\acceptance\nachweise\set1_zaehlerstand_ID742.csv`
- Geprüft: 01.10.2026 10:28 auf Windows 11, Python 3.14.0
- Toleranz: 0.001 kWh

| Prüfung | Status | Ist |
|---|:---:|---|
| Kopfzeile ist `timestamp,value` | ✅ | timestamp,value |
| Alle Zeilen: ganze Zahl, Zahl | ✅ | 0 fehlerhaft |
| Mindestens 1 Datenzeile | ✅ | 2 Zeilen |
| Zeitstempel aufsteigend | ✅ |  |
| Keine doppelten Zeitstempel | ✅ | 0 doppelt |
| Abstände (Info: kleinster Zeitabstand, FA-10) | ℹ️ | 60 min × 1 |
| Zeilenende (Info) | ℹ️ | LF (\n) |
| Nachkommastellen (Info) | ℹ️ | 4 |
| Zeitraum (Info) | ℹ️ | 2024-01-14 23:00 UTC / 00:00 Zürich bis 2024-01-15 00:00 UTC / 01:00 Zürich |

**Gesamt: ✅ bestanden**
### Zählerstand ID742 gegen ESL-Ablesungen

- Datei: `docs\acceptance\nachweise\set1_zaehlerstand_ID742.csv`
- Geprüft: 01.10.2026 10:28 auf Windows 11, Python 3.14.0
- Toleranz: 0.001 kWh

CSV deckt 2024-01-14 23:00 UTC / 00:00 Zürich bis 2024-01-15 00:00 UTC / 01:00 Zürich ab.

| ESL-Zeitpunkt | Soll kWh | Ist kWh (gleicher Zeitpunkt) | Differenz | Status | Hinweis |
|---|---:|---:|---:|:---:|---|
| 2024-01-14 23:00 UTC / 00:00 Zürich | 1000.0000 | 1000.0000 | +0.0000 | ✅ | |
| 2024-01-15 00:00 UTC / 01:00 Zürich | 1000.8500 | 1000.8500 | +0.0000 | ✅ | |

Geprüfte ESL-Zeitpunkte im CSV-Zeitraum: 2

**Gesamt: ✅ bestanden**
### CSV-Format

- Datei: `docs\acceptance\nachweise\set1_verbrauch_ID742.csv`
- Geprüft: 01.10.2026 10:28 auf Windows 11, Python 3.14.0
- Toleranz: 0.001 kWh

| Prüfung | Status | Ist |
|---|:---:|---|
| Kopfzeile ist `timestamp,value` | ✅ | timestamp,value |
| Alle Zeilen: ganze Zahl, Zahl | ✅ | 0 fehlerhaft |
| Mindestens 1 Datenzeile | ✅ | 6 Zeilen |
| Zeitstempel aufsteigend | ✅ |  |
| Keine doppelten Zeitstempel | ✅ | 0 doppelt |
| Abstände (Info: kleinster Zeitabstand, FA-10) | ℹ️ | 15 min × 5 |
| Zeilenende (Info) | ℹ️ | LF (\n) |
| Nachkommastellen (Info) | ℹ️ | 4 |
| Zeitraum (Info) | ℹ️ | 2024-01-14 22:45 UTC / 23:45 Zürich bis 2024-01-15 00:00 UTC / 01:00 Zürich |

**Gesamt: ✅ bestanden**
### Verbrauch ID742 gegen SDAT

- Datei: `docs\acceptance\nachweise\set1_verbrauch_ID742.csv`
- Geprüft: 01.10.2026 10:28 auf Windows 11, Python 3.14.0
- Toleranz: 0.001 kWh

Zeitstempel in der CSV entsprechen dem Intervall**ende** (wie FA-05 verlangt).

| Prüfung | Ergebnis | Status |
|---|---|:---:|
| CSV-Zeilen | 6 | ℹ️ |
| davon mit SDAT-Soll verglichen | 6 | ✅ |
| Abweichungen ≥ 0.001 kWh | 0 | ✅ |
| CSV-Zeitpunkte ohne SDAT-Wert | 0 | ✅ |

**Gesamt: ✅ bestanden**

#### G-07 Echte ESL-Stichproben

| ESL-Zeitpunkt (Zürich) | Sensor | Soll (sollwerte.py) | Ist (Diagramm-Tooltip) | Differenz | Status |
|---|---|---:|---:|---:|:---:|
| | | | | | |
| | | | | | |
| | | | | | |

---

## Durchlauf 2 – Endabnahme auf integriertem Abgabe-Commit

_(gleiche Struktur wie Durchlauf 1; Commit muss der Abgabe-Commit sein)_
