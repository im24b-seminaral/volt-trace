# Befunde aus der Abnahme (Issue #15)

Befunde werden hier **dokumentiert, nicht behoben**. Jeder Befund geht als Kommentar oder
eigenes Issue an den Dateieigentümer:

| Bereich | Eigentümer |
|---|---|
| Diagramme, ChartForm, Zeitdarstellung (FA-08, FA-09, NFA-05) | **#11** |
| Python-Verarbeitung, Upload, Export, Fortschritt (FA-01, FA-02, FA-10, NFA-01, NFA-06) | **#12** |
| PYTHON.md, Architektur-Doku | **#14** |

Ein Befund wird erst geschlossen, wenn die Prüfung auf einem neuen Commit wiederholt und bestanden ist.

---

## Vorlage (kopieren)

### BEF-__ – _Kurztitel_

| | |
|---|---|
| Prüfung | z. B. G-04 |
| Schwere | 🔴 Muss (Abnahme scheitert) · 🟠 Soll · 🟡 Kann |
| Eigentümer | #11 / #12 / #14 |
| Commit | `_______` |
| Umgebung | OS, Browser + Version, Python, Node |
| Gefunden am | TT.MM.2026 HH:MM |
| Status | offen / gemeldet am … / behoben in `…` / nachgeprüft ✅ |

**Schritte zum Nachstellen**
1. `npm run dev` starten, http://localhost:3000 öffnen
2. …
3. …

**Erwartet (Soll):** … (Quelle: Pflichtenheft FA-__ / `tests/acceptance/SOLLWERTE.md`)

**Tatsächlich (Ist):** …

**Nachweis:** Screenshot `nachweise/…png`, Ausgabe von `csv_pruefen.py` …

---

## Befunde

### BEF-01 – UI blockiert über 3 Sekunden bei Datenverarbeitung

| | |
|---|---|
| Prüfung | L-04 |
| Schwere | 🟠 Soll |
| Eigentümer | #12 |
| Commit | `90577f2` |
| Umgebung | Windows 10, Opera 136.0 / Chrome 152.0, Python 3.10.0, Node v22.12.0 |
| Gefunden am | 01.10.2026 11:11 |
| Status | offen |

**Schritte zum Nachstellen**
1. `npm run dev` starten, http://localhost:3001 öffnen
2. DevTools öffnen, in Konsole `longtasks_konsole.js` einfügen
3. Echten Datensatz hochladen
4. `abnahmeErgebnis()` in der Konsole ausführen

**Erwartet (Soll):** Keine Long Tasks > 1000 ms

**Tatsächlich (Ist):** 8 Long Tasks, längster 3223 ms

**Nachweis:** Konsole-Ausgabe im TESTPROTOKOLL.md unter L-04

### BEF-02 – Server-Verarbeitung dauert zu lange (TTFB > 10 s)

| | |
|---|---|
| Prüfung | L-03 |
| Schwere | 🔴 Muss |
| Eigentümer | #12 |
| Commit | `90577f2` |
| Umgebung | Windows 10, Python 3.10.0 |
| Gefunden am | 01.10.2026 11:51 |
| Status | offen |

**Schritte zum Nachstellen**
1. Echten Datensatz (XML-Files.zip, ca. 110 MB) hochladen.
2. Network-Tab beobachten.

**Erwartet (Soll):** Server (TTFB) ≤ 10 s

**Tatsächlich (Ist):** Server-Antwort dauert ca. 40 s. Die Python-CLI (`sort-files`) verarbeitet 5179 Dateien synchron während des Upload-Requests.

**Nachweis:** Backend-Logs, siehe TESTPROTOKOLL.md.

### BEF-03 – Kein Fortschrittsbalken beim Upload

| | |
|---|---|
| Prüfung | L-05 |
| Schwere | 🟠 Soll |
| Eigentümer | #12 |
| Commit | `90577f2` |
| Umgebung | Windows 10 |
| Gefunden am | 01.10.2026 11:51 |
| Status | offen |

**Schritte zum Nachstellen**
1. Grossen Datensatz hochladen.
2. UI während des Uploads beobachten.

**Erwartet (Soll):** Fortschrittsbalken oder Ladeindikator sichtbar.

**Tatsächlich (Ist):** Kein nativer Fortschrittsbalken sichtbar (Next.js Server Actions blockieren einfach bis sie fertig sind, UI "friert" scheinbar ein).

**Nachweis:** UI-Test.
