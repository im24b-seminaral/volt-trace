# Soll-Werte der Prüf-Dateien (Musterlösung)

Diese Werte sind **von Hand gerechnet** und mit `scripts/acceptance/sollwerte.py` nachgeprüft.
Sie gelten für die Prüf-Dateien in `fixtures/`. Für die echten Daten berechnet `sollwerte.py`
die Soll-Werte direkt aus den XML-Dateien.

---

## Set 1 – `fixtures/set1_normal/` (bzw. `fixtures/set1_normal.zip`)

### Was in den Dateien steht

| Datei | Inhalt |
|---|---|
| `sdat_ID742_original.xml` | ID742 (Bezug), 6 Viertelstunden ab 14.01.2024 22:30 UTC: 0.40 · 0.60 · 0.25 · 0.30 · **0.00** · 0.10 · erstellt 15.01. 06:00 |
| `sdat_ID742_korrektur.xml` | ID742, **Korrektur** für 23:30 UTC: **0.20** · erstellt 16.01. 06:00 (neuer!) · ohne `Resolution`-Feld |
| `sdat_ID735.xml` | ID735 (Einspeisung), 6 Viertelstunden ab 22:30 UTC: 0.00 · 0.00 · 0.05 · 0.05 · 0.10 · 0.00 |
| `esl_2024-01-15_0000.xml` | Ablesung 15.01.2024 **00:00 Zürich** = 14.01. 23:00 UTC · Bezug 600.0 + 400.0 · Einspeisung 10.1 + 5.9 · dazu `1-1:1.8.0 = 99999` (muss ignoriert werden) |
| `esl_2024-01-15_0100.xml` | Ablesung 15.01.2024 **01:00 Zürich** = 15.01. 00:00 UTC · Bezug 600.5 + 400.35 · Einspeisung 10.2 + 6.0 |

Die Werte sind so gewählt, dass SDAT und ESL **genau zusammenpassen**. Hier darf es also keine Abweichung geben.

### G-01: ESL Hochtarif + Niedertarif

| Sensor | Zeit Zürich | Zeit UTC | Unix-Zeit | Soll kWh |
|---|---|---|---:|---:|
| ID742 | 15.01. 00:00 | 14.01. 23:00 | 1705273200 | **1000.0000** |
| ID742 | 15.01. 01:00 | 15.01. 00:00 | 1705276800 | **1000.8500** |
| ID735 | 15.01. 00:00 | 14.01. 23:00 | 1705273200 | **16.0000** |
| ID735 | 15.01. 01:00 | 15.01. 00:00 | 1705276800 | **16.2000** |

Falsch wäre z. B. 100999.0 (wenn `1-1:1.8.0` mitgezählt würde).

### G-02: Tagessummen Verbrauch (Zürcher Kalendertag)

| Sensor | Tag | Anzahl Werte | Soll kWh | Warum |
|---|---|---:|---:|---|
| ID742 | 14.01.2024 | 2 | **1.0000** | 0.40 + 0.60 (23:30 und 23:45 Zürich) |
| ID742 | 15.01.2024 | 4 | **0.8500** | 0.25 + 0.30 + **0.20** + 0.10 (Korrektur gewinnt!) |
| ID735 | 14.01.2024 | 2 | **0.0000** | |
| ID735 | 15.01.2024 | 4 | **0.2000** | 0.05 + 0.05 + 0.10 + 0.00 |

Häufige Fehler, die diese Werte aufdecken:
- 15.01. = **0.65** → die alte Datei hat gewonnen statt der Korrektur (FA-06)
- 14.01. = 0, 15.01. = 1.85 → Tagesgrenze in UTC statt Zürich (NFA-05)

### G-03/G-04: Zählerstand (15 min, Zeitstempel = Intervall**ende**, wie FA-05 verlangt)

| Zeit UTC | Zeit Zürich | Unix-Zeit | ID742 Soll | ID735 Soll |
|---|---|---:|---:|---:|
| 14.01. 22:45 | 23:45 | 1705272300 | 999.4000 | 16.0000 |
| 14.01. 23:00 | 00:00 | 1705273200 | **1000.0000** = ESL | **16.0000** = ESL |
| 14.01. 23:15 | 00:15 | 1705274100 | 1000.2500 | 16.0500 |
| 14.01. 23:30 | 00:30 | 1705275000 | 1000.5500 | 16.1000 |
| 14.01. 23:45 | 00:45 | 1705275900 | 1000.7500 | 16.2000 |
| 15.01. 00:00 | 01:00 | 1705276800 | **1000.8500** = ESL | **16.2000** = ESL |

Die Werte vor 23:00 UTC (22:45 = 999.40) gibt es nur, wenn die App **rückwärts** vom ESL-Wert rechnet (FA-07).

### G-05: Verbrauch (15 min, Zeitstempel = Intervallende)

| Zeit UTC | Unix-Zeit | ID742 Soll | ID735 Soll |
|---|---:|---:|---:|
| 14.01. 22:45 | 1705272300 | 0.4000 | 0.0000 |
| 14.01. 23:00 | 1705273200 | 0.6000 | 0.0000 |
| 14.01. 23:15 | 1705274100 | 0.2500 | 0.0500 |
| 14.01. 23:30 | 1705275000 | 0.3000 | 0.0500 |
| 14.01. 23:45 | 1705275900 | **0.2000** | 0.1000 |
| 15.01. 00:00 | 1705276800 | 0.1000 | 0.0000 |

### Zum Vergleich: was der Stand vom 30.09.2026 (Commit `120bc71`) liefert

Damit du einen Unterschied richtig einordnen kannst:

| | Stand 30.09. | Soll | Befund |
|---|---|---|---|
| Zeitstempel | Intervall**beginn** (23:00 für 23:00–23:15) | Intervall**ende** | FA-05 → #12 |
| Zählerstand bei 23:00 UTC | 1000.25 | 1000.00 | FA-05 → #12 |
| Werte vor dem ersten ESL | fehlen | 999.40 … | FA-07 → #12 |
| Tagessummen | 1.00 / 0.85 | 1.00 / 0.85 | ✅ |

---

## Set 2 – `fixtures/set2_fehler/` (Fehler provozieren, R-01/R-02)

| Datei | Was daran falsch ist | Soll-Verhalten |
|---|---|---|
| `kaputt.xml` | kein XML | Meldung, App läuft weiter |
| `leer.xml` | 0 Bytes | Meldung, App läuft weiter |
| `unbekannt.xml` | gültiges XML, aber weder SDAT noch ESL | Meldung «unbekanntes Format» |
| `sdat_ohne_startzeit.xml` | SDAT ohne `StartDateTime` | Meldung, Datei übersprungen |
| `sdat_gueltig_ID742.xml` | korrekt | **wird trotzdem verarbeitet**, Sensor ID742 erscheint |

Bestanden, wenn: alle 4 fehlerhaften Dateien gemeldet werden, die gültige Datei verarbeitet wird
und die Oberfläche bedienbar bleibt (kein weisser Bildschirm, kein ewiges Laden).
