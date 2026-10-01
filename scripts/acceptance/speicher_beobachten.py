"""
speicher_beobachten.py - Misst den Arbeitsspeicher (RAM), während du im Browser hochlädst.

So benutzt du es:
  1. npm run dev läuft schon, Browser ist offen.
  2. In einem ZWEITEN Terminal starten (aus dem Hauptordner des Repositorys):
        python scripts/acceptance/speicher_beobachten.py
  3. Im Browser den Ordner/die ZIP hochladen und warten, bis das Diagramm da ist.
  4. Im Terminal Ctrl+C drücken. Das Skript gibt die Höchstwerte aus.

Gemessen wird alle 0.2 s:
  - "Datenverarbeitung" = Python-Prozesse (volt_trace / uvicorn / python)  → Grenze < 1 GB
  - "Node/Next.js"      = node-Prozesse (zur Info)
  - Auslagerung (Swap) vorher/nachher                                     → darf nicht wachsen

Nur Standardbibliothek. macOS/Linux über "ps", Windows über "tasklist".
Option --filter TEXT: nur Python-Prozesse zählen, deren Befehlszeile TEXT enthält.
"""

import argparse
import platform
import re
import subprocess
import sys
import time
from datetime import datetime

GRENZE_MB = 1024
SYSTEM = platform.system()


def prozesse():
    """-> Liste von (pid, rss_mb, name, befehlszeile)."""
    if SYSTEM == "Windows":
        ausgabe = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
        liste = []
        for zeile in ausgabe.splitlines():
            teile = [t.strip('"') for t in zeile.split('","')]
            if len(teile) >= 5:
                kb = int(re.sub(r"\D", "", teile[4]) or 0)
                liste.append((teile[1], kb / 1024, teile[0].lower(), teile[0].lower()))
        return liste
    ausgabe = subprocess.run(["ps", "-axo", "pid=,rss=,comm=,args="], capture_output=True, text=True).stdout
    liste = []
    for zeile in ausgabe.splitlines():
        teile = zeile.split(None, 3)
        if len(teile) >= 3 and teile[1].isdigit():
            befehl = teile[3] if len(teile) > 3 else teile[2]
            liste.append((teile[0], int(teile[1]) / 1024, teile[2].lower(), befehl))
    return liste


def swap_belegt_mb():
    try:
        if SYSTEM == "Darwin":
            text = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
            treffer = re.search(r"used\s*=\s*([\d.]+)M", text)
            return float(treffer.group(1)) if treffer else None
        if SYSTEM == "Linux":
            werte = {}
            with open("/proc/meminfo") as f:
                for zeile in f:
                    name, wert = zeile.split(":")
                    werte[name] = int(wert.split()[0])
            return (werte["SwapTotal"] - werte["SwapFree"]) / 1024
    except (OSError, ValueError, KeyError):
        pass
    return None   # Windows: im Task-Manager → Leistung → Arbeitsspeicher "Ausgelagert" ablesen


def ist_python(name, befehl, filter_text):
    if "speicher_beobachten" in befehl:
        return False
    if filter_text:
        return filter_text.lower() in befehl.lower()
    return "python" in name or "volt_trace" in befehl or "uvicorn" in befehl


def main():
    parser = argparse.ArgumentParser(description="RAM-Messung während des Uploads (Issue #15)")
    parser.add_argument("--intervall", type=float, default=0.2)
    parser.add_argument("--filter", default="", help="nur Python-Prozesse mit diesem Text in der Befehlszeile")
    args = parser.parse_args()

    swap_start = swap_belegt_mb()
    start = datetime.now()
    peak_py = peak_node = peak_einzel = 0.0
    peak_py_zeit = None
    peak_prozess = ""
    swap_max = swap_start
    messungen = 0
    print(f"Messung läuft seit {start:%H:%M:%S} … jetzt im Browser hochladen. Ende mit Ctrl+C.")
    try:
        while True:
            liste = prozesse()
            py = [p for p in liste if ist_python(p[2], p[3], args.filter)]
            node = [p for p in liste if "node" in p[2]]
            summe_py = sum(p[1] for p in py)
            if summe_py > peak_py:
                peak_py, peak_py_zeit = summe_py, datetime.now()
            for p in py:
                if p[1] > peak_einzel:
                    peak_einzel, peak_prozess = p[1], p[3][:90]
            peak_node = max(peak_node, sum(p[1] for p in node))
            swap = swap_belegt_mb()
            if swap is not None and (swap_max is None or swap > swap_max):
                swap_max = swap
            messungen += 1
            print(f"\r  Python jetzt {summe_py:7.0f} MB | Peak {peak_py:7.0f} MB | Node Peak {peak_node:7.0f} MB",
                  end="", flush=True)
            time.sleep(args.intervall)
    except KeyboardInterrupt:
        pass

    ende = datetime.now()
    ok = peak_py < GRENZE_MB
    print("\n\n### Speichermessung (L-06 / L-07)\n")
    print(f"- Zeitraum: {start:%d.%m.%Y %H:%M:%S} – {ende:%H:%M:%S} ({messungen} Messungen, alle {args.intervall} s)")
    print(f"- System: {platform.system()} {platform.release()}, Python {platform.python_version()}")
    print(f"- Methode: {'tasklist' if SYSTEM == 'Windows' else 'ps (RSS)'}, Summe aller Python-Prozesse\n")
    print("| Messwert | Ist | Grenze | Status |\n|---|---:|---:|:---:|")
    print(f"| Peak Datenverarbeitung (Python, Summe) | {peak_py:.0f} MB | < {GRENZE_MB} MB | {'✅' if ok else '❌'} |")
    print(f"| Grösster einzelner Python-Prozess | {peak_einzel:.0f} MB | – | ℹ️ |")
    print(f"| Peak Node/Next.js | {peak_node:.0f} MB | – | ℹ️ |")
    if swap_start is None:
        print("| Auslagerung (Swap) | manuell im Task-Manager prüfen | darf nicht wachsen | ⚪ |")
    else:
        zuwachs = (swap_max or 0) - swap_start
        print(f"| Auslagerung (Swap) Zuwachs | {zuwachs:+.0f} MB (Start {swap_start:.0f}, max {swap_max:.0f}) "
              f"| 0 MB | {'✅' if zuwachs <= 1 else '❌'} |")
    if peak_py_zeit:
        print(f"\nPeak um {peak_py_zeit:%H:%M:%S}, grösster Prozess: `{peak_prozess}`")
    if peak_py == 0:
        print("\n⚠️ Kein Python-Prozess gesehen. Lief der Upload während der Messung? Evtl. --filter anpassen.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):          # Windows: ✅/❌ auch bei Umleitung in Datei/pytest
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
