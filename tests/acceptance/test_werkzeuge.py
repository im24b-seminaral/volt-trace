"""
test_werkzeuge.py - Prüft die PRÜFWERKZEUGE selbst (nicht die App).

Bevor man der App einen Fehler vorwirft, muss sicher sein, dass die eigene
Musterlösung stimmt. Diese Tests vergleichen sollwerte.py und csv_pruefen.py
mit den von Hand gerechneten Werten aus SOLLWERTE.md.

Ausführen aus dem Hauptordner:
    python -m pytest tests/acceptance -q
"""

import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).parent
SKRIPTE = HIER.parents[1] / "scripts" / "acceptance"
SET1 = HIER / "fixtures" / "set1_normal"
sys.path.insert(0, str(SKRIPTE))

from sollwerte import lies_esl_ordner, lies_sdat_ordner, lokal_zu_utc, tagessummen, utc_zu_lokal  # noqa: E402

UTC = timezone.utc


def ts(unix):
    return datetime.fromtimestamp(unix, tz=UTC)


def test_esl_hoch_plus_niedertarif():
    esl = lies_esl_ordner(SET1)
    assert esl["ID742"] == {ts(1705273200): 1000.0, ts(1705276800): 1000.85}
    assert esl["ID735"] == {ts(1705273200): 16.0, ts(1705276800): 16.2}


def test_neueste_datei_gewinnt():
    sdat = lies_sdat_ordner(SET1)["ID742"]
    assert sdat[ts(1705275000)][1] == 0.20          # 23:30 UTC: Korrektur statt 0.00


def test_aufloesung_ohne_resolution_feld():
    sdat = lies_sdat_ordner(SET1)["ID742"]
    ende, _vol = sdat[ts(1705275000)]
    assert ende == ts(1705275900)                   # 15 min aus Intervall-Länge berechnet


def test_tagessummen_nach_zuercher_mitternacht():
    sdat = lies_sdat_ordner(SET1)
    id742 = {str(t): v for t, v in tagessummen(sdat["ID742"]).items()}
    id735 = {str(t): v for t, v in tagessummen(sdat["ID735"]).items()}
    assert id742 == {"2024-01-14": 1.0, "2024-01-15": 0.85}
    assert id735 == {"2024-01-14": 0.0, "2024-01-15": 0.2}


def test_zeitzone_winter_sommer_umstellung():
    assert lokal_zu_utc(datetime(2024, 1, 15, 0, 0)) == datetime(2024, 1, 14, 23, 0, tzinfo=UTC)
    assert lokal_zu_utc(datetime(2024, 7, 15, 0, 0)) == datetime(2024, 7, 14, 22, 0, tzinfo=UTC)
    assert utc_zu_lokal(datetime(2024, 3, 31, 1, 0, tzinfo=UTC)) == datetime(2024, 3, 31, 3, 0)
    assert utc_zu_lokal(datetime(2024, 10, 27, 1, 0, tzinfo=UTC)) == datetime(2024, 10, 27, 2, 0)


def test_zip_enthaelt_alle_dateien():
    namen = zipfile.ZipFile(HIER / "fixtures" / "set1_normal.zip").namelist()
    assert sorted(Path(n).name for n in namen) == sorted(p.name for p in SET1.glob("*.xml"))


def _csv(tmp_path, zeilen):
    datei = tmp_path / "test.csv"
    datei.write_text("timestamp,value\n" + "".join(f"{t},{v}\n" for t, v in zeilen))
    return datei


def _pruefe(*args):
    return subprocess.run([sys.executable, str(SKRIPTE / "csv_pruefen.py"), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def test_csv_pruefen_akzeptiert_richtige_zaehlerstaende(tmp_path):
    richtig = _csv(tmp_path, [(1705272300, "999.4000"), (1705273200, "1000.0000"), (1705274100, "1000.2500"),
                              (1705275000, "1000.5500"), (1705275900, "1000.7500"), (1705276800, "1000.8500")])
    assert _pruefe("esl", richtig, "--xml", SET1, "--sensor", "ID742").returncode == 0
    assert _pruefe("format", richtig).returncode == 0


def test_csv_pruefen_findet_falschen_zaehlerstand(tmp_path):
    falsch = _csv(tmp_path, [(1705273200, "1000.2500"), (1705276800, "1000.8500")])
    ergebnis = _pruefe("esl", falsch, "--xml", SET1, "--sensor", "ID742")
    assert ergebnis.returncode == 1
    assert "+0.2500" in ergebnis.stdout


def test_csv_pruefen_findet_kaputte_csv(tmp_path):
    datei = tmp_path / "kaputt.csv"
    datei.write_text("zeit;wert\nabc;1\n")
    assert _pruefe("format", datei).returncode == 1


def test_csv_pruefen_verbrauch(tmp_path):
    richtig = _csv(tmp_path, [(1705272300, "0.4000"), (1705273200, "0.6000"), (1705274100, "0.2500"),
                              (1705275000, "0.3000"), (1705275900, "0.2000"), (1705276800, "0.1000")])
    assert _pruefe("verbrauch", richtig, "--xml", SET1, "--sensor", "ID742").returncode == 0
    alt = _csv(tmp_path, [(1705275900, "0.0000")])                # alte Datei statt Korrektur
    assert _pruefe("verbrauch", alt, "--xml", SET1, "--sensor", "ID742").returncode == 1
