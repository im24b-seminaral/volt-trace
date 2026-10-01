"""
sollwerte.py - Unabhängige Soll-Werte für die Abnahme (Issue #15).

Liest SDAT- und ESL-XML-Dateien SELBST ein, ohne Code aus volt_trace zu benutzen.
So entsteht eine zweite, unabhängige Rechnung, gegen die die App geprüft wird.

Nur Standardbibliothek, keine Zusatzpakete (Vorgabe Issue #15).
Die Zeitzone Europe/Zurich wird selbst berechnet (EU-Sommerzeitregel), damit das
Skript auch unter Windows ohne das Paket "tzdata" läuft.

Wird von den anderen Skripten importiert; kann auch direkt gestartet werden:
    python scripts/acceptance/sollwerte.py <ordner-mit-xml>
"""

import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
OBIS_ZU_SENSOR = {"1-1:1.8": "ID742", "1-1:2.8": "ID735"}   # Bezug / Einspeisung


# ---------------------------------------------------------------- Zeitzone Zürich

def _letzter_sonntag(jahr: int, monat: int) -> date:
    tag = date(jahr, monat + 1, 1) - timedelta(days=1) if monat < 12 else date(jahr, 12, 31)
    return tag - timedelta(days=(tag.weekday() + 1) % 7)


def _sommerzeit_utc(jahr: int):
    """Beginn und Ende der Sommerzeit in UTC (EU-Regel: letzter So. März/Okt., 01:00 UTC)."""
    beginn = datetime.combine(_letzter_sonntag(jahr, 3), datetime.min.time(), UTC) + timedelta(hours=1)
    ende = datetime.combine(_letzter_sonntag(jahr, 10), datetime.min.time(), UTC) + timedelta(hours=1)
    return beginn, ende


def utc_offset_zuerich(zeit_utc: datetime) -> timedelta:
    beginn, ende = _sommerzeit_utc(zeit_utc.year)
    return timedelta(hours=2) if beginn <= zeit_utc < ende else timedelta(hours=1)


def utc_zu_lokal(zeit_utc: datetime) -> datetime:
    """UTC -> Zürcher Wanduhrzeit (ohne tzinfo)."""
    return (zeit_utc + utc_offset_zuerich(zeit_utc)).replace(tzinfo=None)


def lokal_zu_utc(lokal: datetime) -> datetime:
    """Zürcher Wanduhrzeit (ohne tzinfo) -> UTC. Bei doppelter Stunde im Oktober: Sommerzeit."""
    for stunden in (2, 1):
        kandidat = (lokal - timedelta(hours=stunden)).replace(tzinfo=UTC)
        if utc_offset_zuerich(kandidat) == timedelta(hours=stunden):
            return kandidat
    return (lokal - timedelta(hours=1)).replace(tzinfo=UTC)   # Lücke im März


def parse_utc(text: str) -> datetime:
    text = text.strip().replace("Z", "+00:00")
    zeit = datetime.fromisoformat(text)
    return zeit if zeit.tzinfo else zeit.replace(tzinfo=UTC)


# ---------------------------------------------------------------- XML-Hilfen

def _name(tag: str) -> str:
    """Tag-Name ohne Namensraum: '{http://www.strom.ch}Volume' -> 'Volume'."""
    return tag.rsplit("}", 1)[-1]


def _erstes(element, name):
    for kind in element.iter():
        if _name(kind.tag) == name and kind.text and kind.text.strip():
            return kind.text.strip()
    return None


# ---------------------------------------------------------------- SDAT

def lies_sdat_datei(pfad: Path):
    """-> (creation, sensor, [(beginn_utc, ende_utc, volumen)]) oder None, wenn nicht SDAT/unvollständig."""
    try:
        root = ET.parse(pfad).getroot()
    except (ET.ParseError, OSError):
        return None
    if not root.tag.startswith("{http://www.strom.ch}"):
        return None
    doc_id, creation, start = _erstes(root, "DocumentID"), _erstes(root, "Creation"), _erstes(root, "StartDateTime")
    if not (doc_id and creation and start):
        return None
    sensor = doc_id.rsplit("_", 1)[-1]
    start = parse_utc(start)
    beobachtungen = []
    for obs in root.iter():
        if _name(obs.tag) == "Observation":
            seq, vol = _erstes(obs, "Sequence"), _erstes(obs, "Volume")
            if seq and vol:
                beobachtungen.append((int(seq), float(vol)))
    if not beobachtungen:
        return None

    aufloesung = None
    for res in root.iter():          # äusseres <Resolution> enthält <Resolution>Zahl</> und <Unit>
        if _name(res.tag) == "Resolution" and len(res):
            zahl = einheit = None
            for kind in res:
                if _name(kind.tag) == "Resolution":
                    zahl = (kind.text or "").strip()
                elif _name(kind.tag) == "Unit":
                    einheit = (kind.text or "").strip().upper()
            if zahl and zahl.isdigit():
                aufloesung = int(zahl) * (60 if einheit in ("HOUR", "HOURS", "H") else 1)
                break
    if aufloesung is None:
        ende = _erstes(root, "EndDateTime")
        if not ende:
            return None
        aufloesung = int((parse_utc(ende) - start).total_seconds() // 60 // len(beobachtungen))
    schritt = timedelta(minutes=aufloesung)
    werte = [(start + (seq - 1) * schritt, start + seq * schritt, vol) for seq, vol in beobachtungen]
    return parse_utc(creation), sensor, werte


def lies_sdat_ordner(ordner: Path):
    """-> {sensor: {beginn_utc: (ende_utc, volumen)}}  (neueste Creation gewinnt, bei Gleichstand Dateiname)."""
    dateien = []
    for pfad in sorted(Path(ordner).rglob("*.xml")):
        ergebnis = lies_sdat_datei(pfad)
        if ergebnis:
            dateien.append((ergebnis[0], pfad.name, ergebnis[1], ergebnis[2]))
    dateien.sort(key=lambda d: (d[0], d[1]))
    pro_sensor = defaultdict(dict)
    for _creation, _name_, sensor, werte in dateien:
        for beginn, ende, vol in werte:
            pro_sensor[sensor][beginn] = (ende, vol)       # spätere Datei überschreibt
    return dict(pro_sensor)


def tagessummen(sdat_sensor: dict):
    """{beginn_utc: (ende, vol)} -> {lokales Datum: summe}. Tag = Zürcher Datum des Intervallbeginns."""
    summen = defaultdict(float)
    for beginn, (_ende, vol) in sdat_sensor.items():
        summen[utc_zu_lokal(beginn).date()] += vol
    return {tag: round(summe, 4) for tag, summe in sorted(summen.items())}


# ---------------------------------------------------------------- ESL

def lies_esl_ordner(ordner: Path):
    """-> {sensor: {zeit_utc: zaehlerstand}}  (HT + NT, nur wenn beide vorhanden, nur status V)."""
    ergebnis = defaultdict(dict)
    for pfad in sorted(Path(ordner).rglob("*.xml")):
        try:
            root = ET.parse(pfad).getroot()
        except (ET.ParseError, OSError):
            continue
        if root.tag != "ESLBillingData":
            continue
        for periode in root.iter("TimePeriod"):
            ende = periode.get("end")
            if not ende:
                continue
            zeit = lokal_zu_utc(datetime.fromisoformat(ende))
            register = defaultdict(dict)
            for zeile in periode.iter("ValueRow"):
                obis, wert = zeile.get("obis", ""), zeile.get("value")
                if zeile.get("status", "V") != "V" or wert is None or "." not in obis:
                    continue
                gruppe, nr = obis.rsplit(".", 1)
                if gruppe in OBIS_ZU_SENSOR and nr in ("1", "2"):
                    register[gruppe][nr] = float(wert)
            for gruppe, reg in register.items():
                if "1" in reg and "2" in reg:
                    ergebnis[OBIS_ZU_SENSOR[gruppe]].setdefault(zeit, round(reg["1"] + reg["2"], 4))
    return {s: dict(sorted(w.items())) for s, w in ergebnis.items()}


# ---------------------------------------------------------------- direkt starten

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):          # Windows: ✅/❌ auch bei Umleitung in Datei/pytest
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python scripts/acceptance/sollwerte.py <ordner-mit-xml>")
    ordner = Path(sys.argv[1])
    esl = lies_esl_ordner(ordner)
    sdat = lies_sdat_ordner(ordner)
    print("## ESL-Zählerstände (HT + NT)\n")
    print("| Sensor | Zeit UTC | Zeit Zürich | Soll kWh |\n|---|---|---|---:|")
    for sensor, werte in sorted(esl.items()):
        for zeit, wert in werte.items():
            print(f"| {sensor} | {zeit:%Y-%m-%d %H:%M} | {utc_zu_lokal(zeit):%Y-%m-%d %H:%M} | {wert:.4f} |")
    print("\n## SDAT-Tagessummen (Zürcher Kalendertag)\n")
    print("| Sensor | Tag | Werte | Soll kWh |\n|---|---|---:|---:|")
    for sensor, werte in sorted(sdat.items()):
        anzahl = defaultdict(int)
        for beginn in werte:
            anzahl[utc_zu_lokal(beginn).date()] += 1
        for tag, summe in tagessummen(werte).items():
            print(f"| {sensor} | {tag:%d.%m.%Y} | {anzahl[tag]} | {summe:.4f} |")
