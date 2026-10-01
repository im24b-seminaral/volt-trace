# Testprotokoll Abnahme Volt Trace (Issue #15)

Für jeden Prüfdurchlauf einen neuen Abschnitt anlegen. Ganz oben die Ausgabe von
`python scripts/acceptance/umgebung.py` einfügen. Screenshots unter `docs/acceptance/nachweise/`
ablegen und hier verlinken.

**Status:** ✅ bestanden · ❌ nicht bestanden · ⚪ offen · ℹ️ Info

---

## Durchlauf 1 – Vorbereitung auf aktuellem Stand

### Umgebung

_(hier Ausgabe von `umgebung.py` einfügen)_

| Browser + Version | |
|---|---|

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
| G-01 | 1000.0000 / 1000.8500 / 16.0000 / 16.2000 | | ⚪ | | |
| G-02 | ID742: 1.0000 / 0.8500 | | ⚪ | | |
| G-03 | 15.01. = 0.85 | | ⚪ | | |
| G-04 | < 0.001 kWh | | ⚪ | | |
| G-05 | < 0.001 kWh | | ⚪ | | |
| G-06 | Format ok | | ⚪ | | |
| G-07 | < 0.001 kWh | | ⚪ | | |
| R-01 | 4 gemeldet, 1 verarbeitet | | ⚪ | | |
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

_(Ausgaben von `csv_pruefen.py format / esl / verbrauch` einfügen)_

#### G-07 Echte ESL-Stichproben

| ESL-Zeitpunkt (Zürich) | Sensor | Soll (sollwerte.py) | Ist (Diagramm-Tooltip) | Differenz | Status |
|---|---|---:|---:|---:|:---:|
| | | | | | |
| | | | | | |
| | | | | | |

---

## Durchlauf 2 – Endabnahme auf integriertem Abgabe-Commit

_(gleiche Struktur wie Durchlauf 1; Commit muss der Abgabe-Commit sein)_
