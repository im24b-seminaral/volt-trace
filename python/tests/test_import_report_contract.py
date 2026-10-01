"""
test_import_report_contract.py - prueft den Importbericht gegen unabhaengig
ermittelte Soll-Werte (FA-01, FA-02, NFA-06).

Der Bericht aus `cmd_sort_files` behauptet, wie viele Dateien gefunden,
eingelesen und uebersprungen wurden. Dieser Test glaubt ihm nicht, sondern
vergleicht ihn mit zwei Quellen, die `build_report` nicht kennt:

1. **Dem Eingangsordner.** Jede Datei wird hier selbst geoeffnet und am
   Wurzel-Tag klassifiziert, ZIP-Mitglieder eingeschlossen. Das ergibt die
   Soll-Zahlen je Typ.
2. **Dem Datensatzordner nach dem Lauf.** Was wirklich in `sdat/` und `esl/`
   liegt, ist nicht verhandelbar.

Das ist dasselbe Vorgehen wie in `volt_trace/calc_values.py`: dort werden die
sdat-Files ein zweites Mal gelesen, weil `load_sdat_folder` bereits
dedupliziert hat und die Rohzahlen sonst nicht mehr pruefbar waeren. Hier wird
der Eingangsordner ein zweites Mal gelesen, weil `cmd_sort_files` die Dateien
wegschiebt und danach niemand mehr nachzaehlen kann.

Bewusst NICHT nachgebaut sind die Sicherheitsregeln des ZIP-Entpackens. Ein
Test, der die Regeln spiegelt, prueft nur sich selbst. Geprueft wird deshalb
die Wirkung: nichts verlaesst den Datensatzordner, und jede verworfene Datei
steht mit Grund im Bericht.

Lauf:  pytest python/tests/test_import_report_contract.py -v
"""

import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from volt_trace import cli

SDAT_NS = "{http://www.strom.ch}"
ESL_ROOT = "ESLBillingData"

# Die Schluessel, die die Oberflaeche erwartet (nextjs/src/lib/types.ts).
REPORT_KEYS = ("foundFiles", "processedFiles", "skippedFiles",
               "skippedRecords", "issues", "findings")


# --------------------------------------------------------------------------
# Testdateien
# --------------------------------------------------------------------------

def _sdat(creation: str, volume: str, sensor: str = "ID742", with_start: bool = True) -> str:
    interval = (
        "<rsm:Interval>"
        "<rsm:StartDateTime>2024-01-01T00:00:00Z</rsm:StartDateTime>"
        "<rsm:EndDateTime>2024-01-01T00:15:00Z</rsm:EndDateTime>"
        "</rsm:Interval>"
    ) if with_start else (
        "<rsm:Interval><rsm:EndDateTime>2024-01-01T00:15:00Z</rsm:EndDateTime></rsm:Interval>"
    )
    return (
        '<rsm:Root xmlns:rsm="http://www.strom.ch">'
        f"<rsm:InstanceDocument><rsm:DocumentID>meter_{sensor}</rsm:DocumentID>"
        f"<rsm:Creation>{creation}</rsm:Creation><rsm:Status>V</rsm:Status>"
        f"</rsm:InstanceDocument>{interval}"
        "<rsm:Resolution><rsm:Resolution>15</rsm:Resolution><rsm:Unit>MIN</rsm:Unit></rsm:Resolution>"
        "<rsm:Observation><rsm:Position><rsm:Sequence>1</rsm:Sequence></rsm:Position>"
        f"<rsm:Volume>{volume}</rsm:Volume></rsm:Observation></rsm:Root>"
    )


ESL_OK = (
    '<ESLBillingData><Meter factoryNo="38157930"><TimePeriod end="2024-01-01T00:00:00">'
    '<ValueRow obis="1-1:1.8.1" value="100" status="V"/>'
    '<ValueRow obis="1-1:1.8.2" value="200" status="V"/>'
    '<ValueRow obis="1-1:2.8.1" value="50" status="E"/>'      # Status ungleich V: ein Datensatz
    '<ValueRow obis="1-1:1.8.0" value="99999" status="V"/>'   # falsche obis-Gruppe: still ignoriert
    "</TimePeriod></Meter></ESLBillingData>"
)

ESL_OHNE_REGISTER = (
    '<ESLBillingData><Meter factoryNo="5442313"><TimePeriod end="2024-01-01T00:00:00">'
    '<ValueRow obis="8-1:1.8.0" value="123" status="V"/>'
    "</TimePeriod></Meter></ESLBillingData>"
)


def dateien() -> dict[str, str]:
    """Ein Eingangsordner, der jeden Zweig des Berichts trifft."""
    return {
        # gueltig
        "a/sdat_alt.xml": _sdat("2024-01-01T01:00:00Z", "1.0"),
        "b/sdat_neu.xml": _sdat("2024-01-01T02:00:00Z", "2.5"),       # gewinnt (FA-06)
        "b/sdat_ID735.xml": _sdat("2024-01-01T02:00:00Z", "0.5", "ID735"),
        "esl/referenz.xml": ESL_OK,
        "esl/ohne_register.xml": ESL_OHNE_REGISTER,                   # Meter uebergangen (FA-04)
        # beim Sortieren verworfen
        "kaputt.xml": "<broken>",
        "leer.xml": "",
        "unbekannt.xml": "<etwas><anderes/></etwas>",
        "notizen.txt": "kein XML",
        # als sdat einsortiert, dann vom Parser verworfen
        "c/sdat_ohne_startzeit.xml": _sdat("2024-01-01T03:00:00Z", "3.0", with_start=False),
    }


# --------------------------------------------------------------------------
# Unabhaengiges Soll: den Eingangsordner selbst zaehlen
# --------------------------------------------------------------------------

def _wurzel_tag(daten: bytes) -> str | None:
    try:
        return ET.fromstring(daten).tag
    except ET.ParseError:
        return None


def _klassifiziere(name: str, daten: bytes) -> str:
    """sdat, esl oder other - allein am Wurzel-Tag, wie _detect_file_type."""
    if not name.lower().endswith(".xml"):
        return "other"
    tag = _wurzel_tag(daten)
    if tag is None:
        return "other"
    if tag.startswith(SDAT_NS):
        return "sdat"
    if tag == ESL_ROOT:
        return "esl"
    return "other"


def _ignoriert(name: str) -> bool:
    teile = name.replace("\\", "/").split("/")
    return ("__MACOSX" in teile or teile[-1].startswith("._")
            or teile[-1] == ".DS_Store" or not teile[-1])


def soll_aus_eingang(src: Path) -> Counter:
    """
    Zaehlt den unberuehrten Eingangsordner je Typ.

    Muss vor cmd_sort_files laufen: danach sind die Dateien verschoben.
    ZIP-Archive werden gelesen, nicht entpackt.
    """
    soll: Counter = Counter()
    for pfad in sorted(p for p in src.rglob("*") if p.is_file() or p.is_symlink()):
        name = pfad.relative_to(src).as_posix()
        if _ignoriert(name):
            continue
        if pfad.is_symlink():
            soll["other"] += 1
            continue
        if pfad.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(pfad) as archiv:
                    for info in archiv.infolist():
                        if info.is_dir() or _ignoriert(info.filename):
                            continue
                        try:
                            inhalt = archiv.read(info)
                        except Exception:
                            soll["unlesbar"] += 1
                            continue
                        soll[_klassifiziere(info.filename, inhalt)] += 1
            except (zipfile.BadZipFile, OSError):
                soll["unlesbar"] += 1
            continue
        soll[_klassifiziere(name, pfad.read_bytes())] += 1
    return soll


# --------------------------------------------------------------------------
# Bericht lesen, egal ob die Zahlen flach oder je Typ kommen
# --------------------------------------------------------------------------

def je_typ(wert) -> dict[str, int]:
    """
    found/staged kommen je nach Stand als Zahl oder als dict je Typ
    (found_by_type in cli.py). Beides wird hier auf ein dict gebracht.
    """
    if isinstance(wert, dict):
        return {str(k): int(v) for k, v in wert.items()}
    return {"gesamt": int(wert)}


def summe(wert) -> int:
    return sum(je_typ(wert).values())


def importiere(raw: Path, ziel: Path, capsys) -> tuple[dict, object, object, list]:
    cli.cmd_sort_files(str(raw), str(ziel))
    ausgabe = capsys.readouterr().out
    # Der Fortschritt geht auf stderr, der Bericht ist die letzte Zeile auf stdout.
    bericht = json.loads([z for z in ausgabe.splitlines() if z.strip()][-1])
    sdat, esl, uebersprungen = cli._load(str(ziel))
    return bericht, sdat, esl, list(uebersprungen)


def xml_dateien(ordner: Path) -> list[Path]:
    if not ordner.exists():
        return []
    return sorted(p for p in ordner.rglob("*") if p.is_file() and p.suffix.lower() == ".xml")


@pytest.fixture
def lauf(tmp_path, capsys):
    """Legt den Eingangsordner an, merkt sich das Soll, laesst dann den Import laufen."""
    raw = tmp_path / "eingang"
    for name, inhalt in dateien().items():
        ziel = raw / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")

    soll = soll_aus_eingang(raw)
    datensatz = tmp_path / "datensatz"
    bericht, sdat, esl, uebersprungen = importiere(raw, datensatz, capsys)
    return {"soll": soll, "bericht": bericht, "sdat": sdat, "esl": esl,
             "uebersprungen": uebersprungen, "datensatz": datensatz, "raw": raw}


# --------------------------------------------------------------------------
# 1. Form
# --------------------------------------------------------------------------

def test_bericht_hat_die_schluessel_die_die_oberflaeche_erwartet(lauf):
    fehlen = [k for k in REPORT_KEYS if k not in lauf["bericht"]]
    assert not fehlen, (
        f"Im Bericht fehlen {fehlen}. Vorhanden sind {sorted(lauf['bericht'])}. "
        "Entweder build_report oder nextjs/src/lib/types.ts anpassen, aber beide gleich."
    )
    assert isinstance(lauf["bericht"]["issues"], list)
    assert isinstance(lauf["bericht"]["findings"], list)


def test_jede_meldung_hat_datei_art_grund_und_anzahl(lauf):
    for meldung in lauf["bericht"]["issues"]:
        assert set(meldung) >= {"file", "kind", "reason", "skippedRecords"}, meldung
        assert meldung["kind"] in {"file", "record", "meter"}, meldung
        assert meldung["file"], meldung
        assert meldung["reason"], f"Meldung ohne Grund: {meldung}"
        assert isinstance(meldung["skippedRecords"], int), meldung


# --------------------------------------------------------------------------
# 2. Die Zahlen gegen den Eingangsordner
# --------------------------------------------------------------------------

def test_gefunden_entspricht_dem_eingangsordner(lauf):
    soll, gefunden = lauf["soll"], je_typ(lauf["bericht"]["foundFiles"])
    assert summe(lauf["bericht"]["foundFiles"]) == sum(soll.values()), (
        f"Bericht zaehlt {summe(lauf['bericht']['foundFiles'])} Dateien, "
        f"im Eingangsordner liegen {sum(soll.values())}: {dict(soll)}"
    )
    # Wenn der Bericht je Typ zaehlt, muss auch jeder Typ stimmen.
    if "gesamt" not in gefunden:
        for typ in ("sdat", "esl"):
            assert gefunden.get(typ, 0) == soll.get(typ, 0), (
                f"{typ}: Bericht {gefunden.get(typ, 0)}, Eingang {soll.get(typ, 0)}")


def test_gefunden_ist_eingelesen_plus_uebersprungen(lauf):
    b = lauf["bericht"]
    assert summe(b["foundFiles"]) == summe(b["processedFiles"]) + summe(b["skippedFiles"]), (
        f"{summe(b['foundFiles'])} gefunden, aber "
        f"{summe(b['processedFiles'])} + {summe(b['skippedFiles'])} gemeldet"
    )


# --------------------------------------------------------------------------
# 3. Die Zahlen gegen den Datensatzordner
# --------------------------------------------------------------------------

def test_einsortiert_wurde_was_auch_wirklich_dort_liegt(lauf):
    auf_platte = len(xml_dateien(lauf["datensatz"] / "sdat")) + len(xml_dateien(lauf["datensatz"] / "esl"))
    datei_skips = sum(1 for m in lauf["uebersprungen"] if m.get("kind") == "file")
    assert summe(lauf["bericht"]["processedFiles"]) == auf_platte - datei_skips, (
        f"{summe(lauf['bericht']['processedFiles'])} eingelesen gemeldet, aber "
        f"{auf_platte} Dateien einsortiert, davon {datei_skips} vom Parser verworfen"
    )


def test_jede_einsortierte_datei_liegt_im_richtigen_ordner(lauf):
    for pfad in xml_dateien(lauf["datensatz"] / "sdat"):
        assert _klassifiziere(pfad.name, pfad.read_bytes()) == "sdat", pfad
    for pfad in xml_dateien(lauf["datensatz"] / "esl"):
        assert _klassifiziere(pfad.name, pfad.read_bytes()) == "esl", pfad


def test_jeder_messwert_zeigt_auf_eine_datei_die_es_gibt(lauf):
    vorhanden = {p.relative_to(lauf["datensatz"] / "sdat").as_posix()
                 for p in xml_dateien(lauf["datensatz"] / "sdat")}
    for werte in lauf["sdat"].values():
        for wert in werte:
            assert wert.source is not None
            assert wert.source.file in vorhanden, (
                f"Messwert verweist auf {wert.source.file}, das es nicht gibt")


# --------------------------------------------------------------------------
# 4. Die Meldungen
# --------------------------------------------------------------------------

def test_keine_meldung_doppelt(lauf):
    paare = [(m["file"], m["reason"], m.get("obis")) for m in lauf["bericht"]["issues"]]
    doppelt = [p for p, n in Counter(paare).items() if n > 1]
    assert not doppelt, f"Doppelte Meldungen: {doppelt}"


def test_keine_meldung_zu_einer_datei_die_eingelesen_wurde(lauf):
    eingelesen = {p.relative_to(lauf["datensatz"] / typ).as_posix()
                  for typ in ("sdat", "esl") for p in xml_dateien(lauf["datensatz"] / typ)}
    parser_skips = {m["file"] for m in lauf["uebersprungen"] if m.get("kind") == "file"}
    for meldung in lauf["bericht"]["issues"]:
        if meldung["kind"] != "file" or meldung["file"] in parser_skips:
            continue
        assert meldung["file"] not in eingelesen, (
            f"{meldung['file']} ist als Fehler gemeldet, liegt aber einsortiert im Datensatz")


def test_uebersprungene_datensaetze_sind_die_summe_der_meldungen(lauf):
    b = lauf["bericht"]
    assert b["skippedRecords"] == sum(m.get("skippedRecords", 0) for m in b["issues"])
    # Die ValueRow mit Status E ist genau ein Datensatz, keine Datei.
    assert b["skippedRecords"] == 1, b["skippedRecords"]


def test_uebergangener_zaehler_ist_eine_meldung_aber_kein_fehlender_datensatz(lauf):
    meter = [m for m in lauf["bericht"]["issues"] if m.get("kind") == "meter"]
    assert any(m.get("meter") == "5442313" for m in meter), meter
    assert all(m["skippedRecords"] == 0 for m in meter)


def test_parser_meldungen_tragen_ihren_dateityp(lauf):
    """cli._load haengt 'type' an, damit der Bericht je Typ zaehlen kann."""
    getaggt = [m for m in lauf["uebersprungen"] if "type" in m]
    if not getaggt:
        pytest.skip("Dieser Stand von cli._load markiert die Skips noch nicht je Typ")
    for meldung in getaggt:
        assert meldung["type"] in {"sdat", "esl"}, meldung


# --------------------------------------------------------------------------
# 5. Die drei Faelle, die weh tun
# --------------------------------------------------------------------------

def test_gueltige_datei_ueberlebt_einen_ordner_voller_kaputter(lauf):
    """set2_fehler in Worten: vier defekte Dateien duerfen die fuenfte nicht mitnehmen."""
    assert "ID742" in lauf["sdat"], "Der gueltige Sensor fehlt im Ergebnis"
    assert lauf["sdat"]["ID742"][0].volume == 2.5, "Nicht die neueste Creation hat gewonnen (FA-06)"
    assert lauf["esl"]["ID742"][0].start_value == 300, "Hoch- und Niedertarif nicht addiert (FA-04)"
    assert summe(lauf["bericht"]["skippedFiles"]) >= 4


def test_ordner_und_zip_melden_dieselben_zahlen(tmp_path, capsys):
    """FA-01: ein ZIP muss zum selben Bericht fuehren wie der entpackte Ordner."""
    inhalt = dateien()

    ordner_raw = tmp_path / "ordner"
    for name, text in inhalt.items():
        ziel = ordner_raw / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text, encoding="utf-8")

    zip_raw = tmp_path / "zip"
    zip_raw.mkdir()
    with zipfile.ZipFile(zip_raw / "datensatz.zip", "w") as archiv:
        for name, text in inhalt.items():
            archiv.writestr(name, text)

    assert soll_aus_eingang(ordner_raw) == soll_aus_eingang(zip_raw)

    aus_ordner, _, _, _ = importiere(ordner_raw, tmp_path / "out_ordner", capsys)
    aus_zip, _, _, _ = importiere(zip_raw, tmp_path / "out_zip", capsys)

    for schluessel in ("foundFiles", "processedFiles", "skippedFiles"):
        assert summe(aus_ordner[schluessel]) == summe(aus_zip[schluessel]), schluessel
    assert aus_ordner["skippedRecords"] == aus_zip["skippedRecords"]
    assert ({m["reason"] for m in aus_ordner["issues"]}
            == {m["reason"] for m in aus_zip["issues"]})


def test_kaputtes_zip_und_unsicherer_pfad_werden_gemeldet_ohne_auszubrechen(tmp_path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "kaputt.zip").write_bytes(b"kein ZIP")
    with zipfile.ZipFile(raw / "unsicher.zip", "w") as archiv:
        archiv.writestr("../ausbruch.xml", _sdat("2024-01-01T01:00:00Z", "1"))

    bericht, sdat, esl, _ = importiere(raw, tmp_path / "out", capsys)

    assert summe(bericht["processedFiles"]) == 0
    assert any("Ungueltiges ZIP" in m["reason"] or "ZIP" in m["reason"] for m in bericht["issues"])
    assert any("Unsicherer Pfad" in m["reason"] for m in bericht["issues"])
    assert not (tmp_path / "ausbruch.xml").exists()
    assert not (raw.parent / "ausbruch.xml").exists()
    assert sdat == esl == {}


def test_leerer_eingang_ergibt_einen_leeren_aber_gueltigen_bericht(tmp_path, capsys):
    raw = tmp_path / "leer"
    raw.mkdir()
    bericht, sdat, esl, _ = importiere(raw, tmp_path / "out", capsys)
    assert summe(bericht["foundFiles"]) == 0
    assert summe(bericht["processedFiles"]) == 0
    assert bericht["issues"] == []
    assert bericht["findings"] == []
    assert sdat == esl == {}


# --------------------------------------------------------------------------
# 6. Der Befund
# --------------------------------------------------------------------------

def _befunde(verhaeltnis: float) -> list[str]:
    """
    Baut einen Datensatz, in dem die sdat-Summe das `verhaeltnis`-fache der
    ESL-Differenz ist, und laesst build_report daraus die Befunde erzeugen.

    Bewusst ueber build_report und nicht ueber den privaten Helfer: der heisst
    je nach Stand anders, die Signatur von build_report ist das, worauf sich
    cli.py stuetzt.
    """
    from datetime import datetime, timedelta, timezone

    from volt_trace.esl import EslMeterReading
    from volt_trace.report import build_report
    from volt_trace.sdat import MeasuredValue

    MeterReading = pytest.importorskip("volt_trace.analysis").MeterReading

    erster = datetime(2024, 1, 1, tzinfo=timezone.utc)
    letzter = erster + timedelta(days=1)
    esl_differenz = 10.0
    menge = esl_differenz * verhaeltnis

    bericht = build_report(
        found_by_type={"sdat": 1, "esl": 1, "other": 0},
        staged_by_type={"sdat": 1, "esl": 1},
        issues=[],
        sdat_data={"ID742": [MeasuredValue(letzter, 1, menge)]},
        esl_data={"ID742": [EslMeterReading(erster, 100.0),
                            EslMeterReading(letzter, 100.0 + esl_differenz)]},
        meter_readings={"ID742": {
            erster: MeterReading(erster, 0.0, 100.0),
            letzter: MeterReading(letzter, menge, 100.0 + menge),
        }},
    )
    return list(bericht["findings"])


def test_faktor_drei_ist_ein_befund_und_kein_fehler():
    """
    Die Beispieldaten stammen aus einer Testanlage mit bekanntem Messfehler
    (NFA-04). Der Unterschied darf gemeldet, aber nicht korrigiert werden.
    """
    pytest.importorskip("volt_trace.report")
    befunde = _befunde(3.0)
    assert befunde, (
        "Die sdat-Summe ist dreimal die ESL-Differenz, build_report meldet aber "
        "keinen Befund. Entweder ist die Regel weg oder sie rechnet anders."
    )
    assert any("Faktor" in b for b in befunde), befunde


def test_passende_werte_ergeben_keinen_befund():
    """Ein Befund ohne Anlass ist so schlimm wie ein fehlender."""
    pytest.importorskip("volt_trace.report")
    assert not [b for b in _befunde(1.0) if "Faktor" in b]


def test_ohne_abweichung_gibt_es_keinen_befund(lauf):
    """Ein Befund ohne Anlass ist so schlimm wie ein fehlender."""
    for befund in lauf["bericht"]["findings"]:
        assert "Faktor 3" not in befund, (
            "Faktor-3-Befund bei Testdaten, die genau zusammenpassen")


# --------------------------------------------------------------------------
# 7. Gegen einen echten Ordner, wenn einer da ist
# --------------------------------------------------------------------------

ECHTE_DATEN = Path(__file__).resolve().parents[2] / "XML-Files"
# Der Beispieldatensatz liegt nicht im Repository. Ein leerer Ordner XML-Files
# existiert aber oft trotzdem, deshalb wird gezaehlt und nicht nur geschaut.
ECHTE_XML = len(xml_dateien(ECHTE_DATEN))


@pytest.mark.skipif(ECHTE_XML == 0,
                    reason="XML-Files/ fehlt oder enthaelt keine XML-Dateien")
def test_echter_datensatz_zaehlt_auf(tmp_path, capsys):
    """
    Derselbe Abgleich am gelieferten Datensatz. Langsam, laeuft nur, wenn
    XML-Files/ daneben liegt und gefuellt ist. Kopiert, weil cmd_sort_files
    verschiebt.
    """
    raw = tmp_path / "raw"
    shutil.copytree(ECHTE_DATEN, raw)
    soll = soll_aus_eingang(raw)

    bericht, sdat, esl, uebersprungen = importiere(raw, tmp_path / "out", capsys)

    assert summe(bericht["foundFiles"]) == sum(soll.values())
    assert summe(bericht["foundFiles"]) == summe(bericht["processedFiles"]) + summe(bericht["skippedFiles"])
    auf_platte = len(xml_dateien(tmp_path / "out" / "sdat")) + len(xml_dateien(tmp_path / "out" / "esl"))
    datei_skips = sum(1 for m in uebersprungen if m.get("kind") == "file")
    assert summe(bericht["processedFiles"]) == auf_platte - datei_skips

    # Es liegen XML-Dateien im Ordner, also muss auch etwas herauskommen.
    assert sdat or esl, (
        f"{ECHTE_XML} XML-Dateien im Ordner, aber kein einziger Sensor eingelesen. "
        f"Gefunden: {je_typ(bericht['foundFiles'])}, Meldungen: {len(bericht['issues'])}")

    # Erst beim vollstaendigen Datensatz sind die beiden Sensoren garantiert
    # (Pflichtenheft Kapitel 4: 5'133 sdat-Files, 47 ESL-Files).
    if ECHTE_XML >= 1000:
        assert {"ID742", "ID735"} <= set(sdat), sorted(sdat)
        assert {"ID742", "ID735"} <= set(esl), sorted(esl)
        assert len(esl["ID742"]) == 45, f"45 Stichtage erwartet, {len(esl['ID742'])} gefunden"