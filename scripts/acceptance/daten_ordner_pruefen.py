"""
daten_ordner_pruefen.py - Zeigt, welche hochgeladenen Datensätze auf dem Server liegen.

Für R-04 (Sitzungen getrennt) und R-05 (Daten werden gelöscht).
Liest nur, löscht nichts.

Aufruf aus dem Hauptordner des Repositorys:
    python scripts/acceptance/daten_ordner_pruefen.py            (Standard: nextjs/data)
    python scripts/acceptance/daten_ordner_pruefen.py <ordner>
"""

import sys
from datetime import datetime
from pathlib import Path


def main():
    ordner = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("nextjs") / "data"
    print(f"### Datensätze in `{ordner}` – {datetime.now():%d.%m.%Y %H:%M:%S}\n")
    if not ordner.exists():
        print("Ordner existiert nicht (keine Daten auf dem Server).")
        return
    eintraege = sorted((p for p in ordner.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)
    if not eintraege:
        print("Keine Datensätze vorhanden. ✅ (falls nach Sitzungsende geprüft)")
        return
    print("| Datensatz | zuletzt geändert | Alter | Dateien | Grösse | Cache-Datei |")
    print("|---|---|---:|---:|---:|:---:|")
    jetzt = datetime.now().timestamp()
    for p in eintraege:
        dateien = [f for f in p.rglob("*") if f.is_file()]
        groesse = sum(f.stat().st_size for f in dateien) / 1024 / 1024
        cache = any(f.name.endswith(".cache") for f in dateien)
        alter = (jetzt - p.stat().st_mtime) / 60
        print(f"| `{p.name}` | {datetime.fromtimestamp(p.stat().st_mtime):%d.%m. %H:%M} | {alter:.0f} min "
              f"| {len(dateien)} | {groesse:.1f} MB | {'ja' if cache else 'nein'} |")
    print(f"\n{len(eintraege)} Datensatz/Datensätze vorhanden.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):          # Windows: ✅/❌ auch bei Umleitung in Datei/pytest
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
