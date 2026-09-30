# Abnahmeprotokoll: Runtime- und Abhängigkeiten v1.0

Pflichtenheft v1.0 — Python **3.14+**, Node.js **24 LTS**, exakte direkte Abhängigkeiten.

## Metadaten (Soll)

| Prüfpunkt | Soll | Nachweis im Repo |
|-----------|------|------------------|
| `requires-python` | `>=3.14` | [`python/pyproject.toml`](../python/pyproject.toml) |
| `engines.node` | `>=24.0.0 <25.0.0` | [`nextjs/package.json`](../nextjs/package.json) |
| Paketversion | `1.0.0` | `pyproject.toml`, `package.json`, `volt_trace.__version__` |
| pytest | exakt `8.4.2` | [`python/requirements.txt`](../python/requirements.txt) |
| shadcn | nur `devDependencies` | `package.json` |
| `cn` | nicht in Direct-Deps | `package.json`, UI nutzt `@/lib/utils` |

## Automatisierte Prüfung (Entwicklungs-CI)

Datum: **2026-09-30**

| Schritt | Befehl | Umgebung | Ergebnis |
|---------|--------|----------|----------|
| Python-Tests | `cd python && python -m pytest -q` | Python **3.12.3** (unter Soll) | **22 passed, 3 skipped** |
| `pip install -e .` | `cd python && pip install -e .` | Python 3.12.3 | **Abgelehnt** (erwartet: `requires-python >=3.14`) |
| Typecheck | `cd nextjs && npm run typecheck` | Node **22.18.0** (unter Soll, `EBADENGINE`) | **OK** |
| Build | `cd nextjs && npm run build` | Node 22.18.0 | **OK** |

Hinweis: Typecheck/Build laufen auf Node 22 mit Warnung; für die **formale Abnahme** sind Python **3.14.x** und Node **24.x** erforderlich.

## Plattformnachweise (manuell auszufüllen)

Nach Installation gemäss [README](../README.md) (frisches venv, `pip install -r requirements.txt`, `pip install -e python`, `npm ci` in `nextjs`):

| Schritt | Windows (Py 3.14, Node 24) | macOS (Py 3.14, Node 24) | Datum | Prüfer |
|---------|---------------------------|--------------------------|-------|--------|
| `python --version` / `node --version` | | | | |
| `pip install -r requirements.txt` + `pip install -e .` | | | | |
| `pytest -q` | | | | |
| `npm ci` | | | | |
| `npm run typecheck` | | | | |
| `npm run build` | | | | |
| `npm run dev` + Upload/Diagramm (Smoke) | | | | |

## Neuinstallation

- [ ] Windows: kompletter Ablauf ohne vorhandenes `python/.venv` und `nextjs/node_modules`
- [ ] macOS: gleicher Ablauf

Ergebnis / Bemerkungen:

---

_Dieses Protokoll ist Teil der Lieferung L4 (Dokumentation / Testprotokoll)._
