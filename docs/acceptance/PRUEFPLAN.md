# Prüfplan Abnahme Volt Trace (Issue #15)

| | |
|---|---|
| Prüfer | Andris Jacob |
| Geprüfter Commit | `________` (aus `scripts/acceptance/umgebung.py`) |
| Pflichtenheft | v0.9 / v1.0 |
| Prüfart | Blackbox über die Web-Oberfläche (`npm run dev`, http://localhost:3000) und CSV-Download |

**Grundsätze**
- Es wird nur über bestehende Schnittstellen geprüft (Browser, Download). Kein Produktionscode wird geändert.
- Jede Messung hält Commit, Umgebung und Messmethode fest (→ `TESTPROTOKOLL.md`).
- Nicht ausgeführte Prüfungen stehen als **⚪ offen**, nie als bestanden.
- Ein roter Befund bleibt rot, bis der Dateieigentümer ihn behoben hat (→ `BEFUNDE.md`).
- Die endgültige Abnahme wird auf dem integrierten Abgabe-Commit wiederholt.

**Status-Zeichen:** ✅ bestanden · ❌ nicht bestanden · ⚪ offen (nicht geprüft) · ℹ️ nur Information

---

## Prüfdaten

| Name | Ort | Zweck |
|---|---|---|
| Set 1 | `tests/acceptance/fixtures/set1_normal/` + `.zip` | kleine Dateien mit bekannten Soll-Werten (`tests/acceptance/SOLLWERTE.md`) |
| Set 2 | `tests/acceptance/fixtures/set2_fehler/` | kaputte und unvollständige Dateien |
| Echt | vollständiger Beispieldatensatz (SDAT + ESL) des Auftraggebers | Zeit, Speicher, echte ESL-Werte |

## Werkzeuge

| Werkzeug | Zweck |
|---|---|
| `scripts/acceptance/umgebung.py` | Commit, OS, RAM, Python/Node-Version |
| `scripts/acceptance/speicher_beobachten.py` | RAM-Peak und Auslagerung während des Uploads |
| `scripts/acceptance/longtasks_konsole.js` | UI-Blockaden > 1 s (Chrome-Konsole) |
| `scripts/acceptance/sollwerte.py` | Soll-Werte direkt aus den XML-Dateien |
| `scripts/acceptance/csv_pruefen.py` | heruntergeladene CSV gegen Soll prüfen |
| `scripts/acceptance/daten_ordner_pruefen.py` | liegen hochgeladene Daten noch auf dem Server? |
| `tests/acceptance/test_werkzeuge.py` | prüft, dass die Werkzeuge selbst richtig rechnen |
| Browser-DevTools (F12) | Tab «Network»: Übertragungszeit; Stoppuhr: Gesamtzeit |

---

## 1. Leistung (NFA-03, NFA-13)

| Nr. | Was wird geprüft | Daten | Wie | Grenze |
|---|---|---|---|---|
| L-01 | Gesamtzeit: Ordner/ZIP wählen → Diagramm sichtbar | Echt | Stoppuhr (Handy) ab Klick «Hochladen» bis Diagramm, 3 Durchläufe, Mittelwert | < 60 s |
| L-02 | Übertragung (Upload) | Echt | DevTools → Network → Upload-Request → Spalte «Time» | ≤ 45 s |
| L-03 | Lesen/Verarbeiten | Echt | L-01 minus L-02, bzw. Server-Antwortzeit «Waiting (TTFB)» des Upload-Requests | ≤ 10 s |
| L-04 | Keine UI-Blockade | Echt | `longtasks_konsole.js` in Chrome, ganzer Durchlauf | keine > 1000 ms |
| L-05 | Fortschritt sichtbar | Echt | von Hand beobachten, Screenshot während Upload | sichtbar |
| L-06 | Peak-Speicher Datenverarbeitung | Echt | `speicher_beobachten.py` während L-01 | < 1 GB |
| L-07 | Notebook 8 GB RAM ohne Auslagern | Echt | auf 8-GB-Gerät: `speicher_beobachten.py` (Swap-Zuwachs) + Screenshot Aktivitätsmonitor/Task-Manager | Zuwachs 0 |

## 2. Genauigkeit (FA-04, FA-05, FA-06, FA-10, NFA-04, NFA-05)

| Nr. | Was wird geprüft | Daten | Wie | Grenze |
|---|---|---|---|---|
| G-01 | ESL HT + NT im Zählerstand-Diagramm | Set 1 | Diagramm «Zählerstand», 15 min, Tooltip bei 00:00 und 01:00 Zürich ablesen → `SOLLWERTE.md` | < 0.001 kWh |
| G-02 | Tagessummen Verbrauch (Zürcher Tag) | Set 1 | Diagramm «Verbrauch», Tag, Tooltip 14.01. und 15.01. | < 0.001 kWh |
| G-03 | Neueste Datei gewinnt (Korrektur) | Set 1 | G-02 15.01. muss 0.85 sein (nicht 0.65) | exakt |
| G-04 | Zählerstand-CSV gegen ESL | Set 1 + Echt | `csv_pruefen.py esl` | < 0.001 kWh |
| G-05 | Verbrauchs-CSV gegen SDAT | Set 1 + Echt | `csv_pruefen.py verbrauch` | < 0.001 kWh |
| G-06 | CSV-Format beider Exporte | Set 1 + Echt | `csv_pruefen.py format` | Kopf `timestamp,value`, aufsteigend, keine Duplikate |
| G-07 | Echte ESL-Werte im Diagramm | Echt | 3 Stichproben: `sollwerte.py` → Werte im Diagramm-Tooltip suchen | < 0.001 kWh |

**Ausdrücklich nicht gefordert:** FA-07-Konsistenz zwischen SDAT-Summe und ESL-Differenz bei den echten Testanlagenwerten (bekannte Abweichung «Faktor 3», laut Issue ausgenommen). Bei Set 1 passen die Werte dagegen exakt.

## 3. Bedienung pro Browser (FA-01, FA-03, FA-08, FA-09, FA-10, NFA-07, NFA-08)

Jede Zeile in jedem Browser → Ergebnis in `MATRIX.md`.

| Nr. | Was wird geprüft | Bestanden, wenn |
|---|---|---|
| B-01 | Ordner wählen und hochladen | Datei-Anzahl stimmt, Diagramm erscheint |
| B-02 | ZIP wählen und hochladen (`set1_normal.zip`) | gleiche Werte wie B-01 |
| B-03 | Sensor wechseln (ID742 ↔ ID735) | Diagramm wechselt, richtige Werte |
| B-04 | Zeitraum wählen in Lokalzeit | erster/letzter Punkt passen zur Auswahl (Zürich) |
| B-05 | Diagramm wechseln: Verbrauch ↔ Zählerstand | beide erscheinen, Achsen beschriftet |
| B-06 | Auflösung wechseln: Tag ↔ 15 min | beide erscheinen |
| B-07 | CSV-Export Zählerstand | Download klappt, G-06 bestanden |
| B-08 | CSV-Export Verbrauch | Download klappt, G-06 bestanden |

Pflicht-Kombinationen: Windows × 2 Browser, macOS × 2 Browser, dabei Chrome, Firefox und Safari mindestens je einmal. Python 3.14, Node 24.

## 4. Robustheit und Sicherheit (NFA-06, NFA-11, NFA-12)

| Nr. | Was wird geprüft | Daten | Wie | Bestanden, wenn |
|---|---|---|---|---|
| R-01 | Kaputte/leere/unbekannte Dateien | Set 2 | Ordner `set2_fehler` hochladen | alle 4 gemeldet, gültige Datei verarbeitet, UI bedienbar |
| R-02 | Fehler mitten im Upload | Set 1 | während Upload Terminal mit `npm run dev` stoppen, neu starten, Seite neu laden | verständliche Meldung, danach neuer Upload möglich |
| R-03 | Timeout/Abbruch | Echt | Upload starten, Tab während Upload neu laden | kein halber Datensatz bleibt hängen bzw. App bleibt nutzbar |
| R-04 | Sitzungen getrennt | Set 1 | Browser A und privates Fenster B laden je hoch; `daten_ordner_pruefen.py` | 2 getrennte Datensätze, A sieht B nicht |
| R-05 | Löschung bei Sitzungsende | Set 1 | Tab schliessen / Sitzung beenden, Wartezeit laut Konzept, `daten_ordner_pruefen.py` | Datensatz und Cache-Datei gelöscht |
| R-06 | Nur lokal erreichbar | – | von zweitem Gerät im WLAN `http://<IP>:3000` öffnen | nicht erreichbar |

## 5. Liefernachweise

→ `LIEFERNACHWEISE.md`: Produkt/Demo/Präsentation 02.10.2026 08:45, IPERKA-Dokumentation 02.10.2026 12:00 (Europe/Zurich), Zwischenbericht/Freigabe.
