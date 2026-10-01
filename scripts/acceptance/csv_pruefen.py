"""
csv_pruefen.py - Prüft eine CSV-Datei, die über die Web-Oberfläche heruntergeladen wurde.

Die Soll-Werte werden unabhängig aus den XML-Dateien berechnet (sollwerte.py),
nicht mit dem Code der App.

Aufrufe (aus dem Hauptordner des Repositorys):

  Format prüfen:
    python scripts/acceptance/csv_pruefen.py format  <datei.csv>

  Zählerstand-CSV gegen ESL-Ablesungen (Soll = HT + NT zum ESL-Zeitpunkt):
    python scripts/acceptance/csv_pruefen.py esl       <datei.csv> --xml <ordner> --sensor ID742

  Verbrauchs-CSV gegen SDAT-Werte (Soll = Volume pro 15 min):
    python scripts/acceptance/csv_pruefen.py verbrauch <datei.csv> --xml <ordner> --sensor ID742

esl/verbrauch erwarten den vollständigen Export eines Sensors: genau die Soll-Zeitpunkte,
jeder einmal, keine fehlenden, zusätzlichen oder doppelten Zeilen.

Exit-Code 0 = alles bestanden, 1 = mindestens eine Abweichung, 2 = Datei/Aufruf falsch.
Die Ausgabe ist eine Markdown-Tabelle zum Kopieren ins Testprotokoll.
"""

import argparse
import csv
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from sollwerte import lies_esl_ordner, lies_sdat_ordner, utc_zu_lokal

TOLERANZ = 0.001   # kWh, Vorgabe Issue #15


def lies_csv(pfad: Path):
    """-> (kopfzeile, [(zeit_utc, wert, rohzeile)]); bricht mit Exit 2 ab, wenn unlesbar."""
    try:
        with open(pfad, newline="", encoding="utf-8-sig") as f:
            zeilen = list(csv.reader(f))
    except OSError as fehler:
        sys.exit(f"CSV nicht lesbar: {fehler}")
    if not zeilen:
        sys.exit("CSV ist leer.")
    kopf, daten = zeilen[0], []
    for nr, zeile in enumerate(zeilen[1:], start=2):
        if not zeile:
            continue
        try:
            zeit = datetime.fromtimestamp(int(zeile[0]), tz=timezone.utc)
            daten.append((zeit, float(zeile[1]), nr, zeile))
        except (ValueError, IndexError):
            daten.append((None, None, nr, zeile))
    return kopf, daten


def fmt(zeit):
    return f"{zeit:%Y-%m-%d %H:%M} UTC / {utc_zu_lokal(zeit):%H:%M} Zürich" if zeit else "–"


def kopfzeile(titel, csv_pfad):
    print(f"### {titel}\n")
    print(f"- Datei: `{csv_pfad}`")
    print(f"- Geprüft: {datetime.now():%d.%m.%Y %H:%M} auf {platform.system()} {platform.release()}, Python {platform.python_version()}")
    print(f"- Toleranz: {TOLERANZ} kWh\n")


# ------------------------------------------------------------------ format

def pruefe_format(csv_pfad: Path) -> bool:
    kopf, daten = lies_csv(csv_pfad)
    kopfzeile("CSV-Format", csv_pfad)
    ergebnisse = []

    ergebnisse.append(("Kopfzeile ist `timestamp,value`", ",".join(kopf) == "timestamp,value", ",".join(kopf)))
    kaputt = [d for d in daten if d[0] is None]
    ergebnisse.append(("Alle Zeilen: ganze Zahl, Zahl", not kaputt,
                       f"{len(kaputt)} fehlerhaft" + (f", z. B. Zeile {kaputt[0][2]}: {kaputt[0][3]}" if kaputt else "")))
    gut = [d for d in daten if d[0] is not None]
    ergebnisse.append(("Mindestens 1 Datenzeile", bool(gut), f"{len(gut)} Zeilen"))
    zeiten = [d[0] for d in gut]
    ergebnisse.append(("Zeitstempel aufsteigend", zeiten == sorted(zeiten), ""))
    ergebnisse.append(("Keine doppelten Zeitstempel", len(zeiten) == len(set(zeiten)),
                       f"{len(zeiten) - len(set(zeiten))} doppelt"))
    abstaende = {}
    for a, b in zip(zeiten, zeiten[1:]):
        sek = int((b - a).total_seconds())
        abstaende[sek] = abstaende.get(sek, 0) + 1
    haeufig = sorted(abstaende.items(), key=lambda x: -x[1])[:3]
    ergebnisse.append(("Abstände (Info: kleinster Zeitabstand, FA-10)", True,
                       ", ".join(f"{s // 60} min × {n}" for s, n in haeufig) or "–"))
    with open(csv_pfad, "rb") as f:
        roh = f.read()
    zeilenende = "CRLF (\\r\\n)" if b"\r\n" in roh else "LF (\\n)"
    ergebnisse.append(("Zeilenende (Info)", True, zeilenende))
    stellen = {len(d[3][1].split(".")[1]) if "." in d[3][1] else 0 for d in gut}
    ergebnisse.append(("Nachkommastellen (Info)", True, ", ".join(str(s) for s in sorted(stellen))))
    if gut:
        ergebnisse.append(("Zeitraum (Info)", True, f"{fmt(zeiten[0])} bis {fmt(zeiten[-1])}"))

    print("| Prüfung | Status | Ist |\n|---|:---:|---|")
    for name, ok, ist in ergebnisse:
        status = "ℹ️" if "(Info" in name else ("✅" if ok else "❌")
        print(f"| {name} | {status} | {ist} |")
    return all(ok for _n, ok, _i in ergebnisse)


# ------------------------------------------------------------------ esl

def vergleiche_exakt(daten, soll: dict) -> bool:
    """CSV muss genau die Soll-Zeitpunkte enthalten: jeden einmal, keine zusätzlichen, aufsteigend,
    jeder Wert < TOLERANZ vom Soll. Gemeinsam für ESL- und Verbrauchsprüfung (FA-05, FA-10a/b)."""
    zeiten = [d[0] for d in daten if d[0] is not None]
    ist = {d[0]: d[1] for d in daten if d[0] is not None}
    kaputt = [d for d in daten if d[0] is None]
    fehlend = sorted(set(soll) - set(ist))
    zusaetzlich = sorted(set(ist) - set(soll))
    doppelt = len(zeiten) - len(ist)
    abweichungen = [(t, soll[t], ist[t]) for t in sorted(set(ist) & set(soll)) if abs(ist[t] - soll[t]) >= TOLERANZ]
    pruefungen = [
        (f"CSV-Zeilen = Soll-Zeitpunkte ({len(soll)})", len(daten) == len(soll), len(daten)),
        ("Fehlerhafte Zeilen", not kaputt, len(kaputt)),
        ("Fehlende Soll-Zeitpunkte", not fehlend, len(fehlend)),
        ("Zusätzliche Zeitpunkte ohne Soll", not zusaetzlich, len(zusaetzlich)),
        ("Doppelte Zeitstempel", not doppelt, doppelt),
        ("Zeitstempel aufsteigend", zeiten == sorted(zeiten), ""),
        (f"Abweichungen ≥ {TOLERANZ} kWh", not abweichungen, len(abweichungen)),
    ]
    print("| Prüfung | Ergebnis | Status |\n|---|---|:---:|")
    for name, ok, ergebnis in pruefungen:
        print(f"| {name} | {ergebnis} | {'✅' if ok else '❌'} |")
    if abweichungen:
        print("\nErste Abweichungen:\n\n| Zeitpunkt | Soll | Ist | Differenz |\n|---|---:|---:|---:|")
        for t, s, i in abweichungen[:15]:
            print(f"| {fmt(t)} | {s:.4f} | {i:.4f} | {i - s:+.4f} |")
    for titel, liste in (("Fehlende", fehlend), ("Zusätzliche", zusaetzlich)):
        if liste:
            print(f"\n{titel} Zeitpunkte (max. 15): " + ", ".join(fmt(t) for t in liste[:15]))
    return all(ok for _n, ok, _e in pruefungen)


def pruefe_esl(csv_pfad: Path, xml: Path, sensor: str) -> bool:
    _kopf, daten = lies_csv(csv_pfad)
    soll = lies_esl_ordner(xml).get(sensor, {})
    kopfzeile(f"Zählerstand {sensor} gegen ESL-Ablesungen", csv_pfad)
    if not soll:
        print(f"❌ Keine ESL-Werte für {sensor} in `{xml}` gefunden.")
        return False
    # FA-10b: ausschliesslich echte ESL-Ablesezeitpunkte, keine berechneten Zwischenstände.
    print(f"Soll: genau die {len(soll)} ESL-Ablesungen, keine Zwischenwerte.\n")
    return vergleiche_exakt(daten, soll)


# ------------------------------------------------------------------ verbrauch

def pruefe_verbrauch(csv_pfad: Path, xml: Path, sensor: str) -> bool:
    _kopf, daten = lies_csv(csv_pfad)
    sdat = lies_sdat_ordner(xml).get(sensor, {})
    kopfzeile(f"Verbrauch {sensor} gegen SDAT", csv_pfad)
    if not sdat:
        print(f"❌ Keine SDAT-Werte für {sensor} in `{xml}` gefunden.")
        return False

    # FA-05: Zeitstempel = Intervall**ende**. Intervallbeginn wird nie als bestanden gewertet.
    soll = {ende: vol for _beginn, (ende, vol) in sdat.items()}
    ist_zeiten = {d[0] for d in daten if d[0] is not None}
    if ist_zeiten and ist_zeiten <= set(sdat) and ist_zeiten != set(soll):
        print("⚠️ Zeitstempel entsprechen dem Intervall**beginn** (FA-05 verlangt Intervallende → Befund).\n")
    print(f"Soll: genau die {len(soll)} deduplizierten SDAT-Intervalle, Zeitstempel = Intervallende.\n")
    return vergleiche_exakt(daten, soll)


# ------------------------------------------------------------------ main

def main():
    parser = argparse.ArgumentParser(description="CSV aus der Web-Oberfläche prüfen (Issue #15)")
    unter = parser.add_subparsers(dest="art", required=True)
    p = unter.add_parser("format")
    p.add_argument("csv", type=Path)
    for art in ("esl", "verbrauch"):
        p = unter.add_parser(art)
        p.add_argument("csv", type=Path)
        p.add_argument("--xml", type=Path, required=True, help="Ordner mit den hochgeladenen XML-Dateien")
        p.add_argument("--sensor", required=True, help="z. B. ID742")
    args = parser.parse_args()

    if args.art == "format":
        ok = pruefe_format(args.csv)
    elif args.art == "esl":
        ok = pruefe_esl(args.csv, args.xml, args.sensor)
    else:
        ok = pruefe_verbrauch(args.csv, args.xml, args.sensor)
    print(f"\n**Gesamt: {'✅ bestanden' if ok else '❌ nicht bestanden'}**")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):          # Windows: ✅/❌ auch bei Umleitung in Datei/pytest
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
