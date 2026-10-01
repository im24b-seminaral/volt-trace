"""
umgebung.py - Schreibt Commit, Betriebssystem, RAM und Versionen auf.

Zu JEDER Prüfung gehört dieser Block ins Testprotokoll (Akzeptanzkriterium:
"mit Umgebung/Commit/Messmethode protokolliert").

Aufruf aus dem Hauptordner des Repositorys:
    python scripts/acceptance/umgebung.py
"""

import os
import platform
import re
import subprocess
import sys
from datetime import datetime


def befehl(*args):
    try:
        ergebnis = subprocess.run(list(args), capture_output=True, text=True, timeout=15,
                                  shell=(platform.system() == "Windows"))
        if ergebnis.returncode != 0:
            return "?"
        return ergebnis.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return "nicht gefunden"


def ram_gb():
    try:
        system = platform.system()
        if system == "Darwin":
            return int(befehl("sysctl", "-n", "hw.memsize")) / 1024 ** 3
        if system == "Linux":
            with open("/proc/meminfo") as f:
                return int(f.readline().split()[1]) / 1024 ** 2
        if system == "Windows":
            text = befehl("powershell", "-NoProfile", "-Command",
                          "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory")
            return int(re.sub(r"\D", "", text)) / 1024 ** 3
    except (ValueError, OSError):
        pass
    return None


def main():
    commit = befehl("git", "rev-parse", "--short", "HEAD")
    zweig = befehl("git", "rev-parse", "--abbrev-ref", "HEAD")
    sauber = befehl("git", "status", "--porcelain")
    ram = ram_gb()
    print("### Umgebung\n")
    print("| | |\n|---|---|")
    print(f"| Datum/Zeit | {datetime.now():%d.%m.%Y %H:%M} (Europe/Zurich) |")
    print(f"| Commit | `{commit}` auf `{zweig}`{' ⚠️ mit lokalen Änderungen – vor der Messung committen!' if sauber not in ('', '?') else ''} |")
    print(f"| Betriebssystem | {platform.system()} {platform.release()} ({platform.machine()}) |")
    print(f"| Prozessor | {platform.processor() or '?'} , {os.cpu_count()} Kerne |")
    print(f"| Arbeitsspeicher | {f'{ram:.1f} GB' if ram else 'manuell eintragen'} |")
    print(f"| Python | {platform.python_version()} |")
    print(f"| Node | {befehl('node', '-v')} |")
    print(f"| npm | {befehl('npm', '-v')} |")
    print("| Browser + Version | _(von Hand eintragen, z. B. Chrome 141.0)_ |")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):          # Windows: ✅/❌ auch bei Umleitung in Datei/pytest
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
