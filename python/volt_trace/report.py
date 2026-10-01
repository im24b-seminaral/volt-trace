"""
report.py - Baut den Importbericht aus den eingelesenen Daten.

Der Bericht wird einmal beim Upload erzeugt und als import-report.json neben
dem Datensatz abgelegt; die Oberfläche liest ihn, ohne Python erneut zu rufen.
Die Hinweise erklären, was mit den Dateien passiert ist (NFA-06): warum etwas
übersprungen wurde, wie Duplikate aufgelöst wurden und welche Tage von der
Zeitumstellung betroffen sind.
"""

from volt_trace.localtime import (
    LOCAL_TZ,
    consumption_day_bucket,
    local_day_quarter_hours,
)
from volt_trace.sdat import SENSOR_DIRECTIONS

FILE_TYPES = ("sdat", "esl")
DIRECTIONS = ("consumption", "feed-in", "other")
NO_TARIFF_PAIRS = "keine vollständigen OBIS-Paare"
QUARTER_HOURS_PER_DAY = 96


def build_report(*, found_by_type: dict[str, int], staged_by_type: dict[str, int],
                 issues: list[dict], sdat_data, esl_data, meter_readings=None) -> dict:
    """found_by_type zählt erkannte Dateien je Typ, staged_by_type die abgelegten.

    Als nicht lesbar gelten nur die Skips der Loader: sie tragen ihren Typ und
    betreffen abgelegte Dateien. Beim Sortieren verworfene Dateien fehlen schon
    in staged_by_type.
    """
    rows = []
    for file_type in FILE_TYPES:
        found = found_by_type.get(file_type, 0)
        unreadable = sum(1 for issue in issues
                         if issue.get("kind") == "file" and issue.get("type") == file_type)
        processed = staged_by_type.get(file_type, 0) - unreadable
        rows.append({"type": file_type, "found": found, "processed": processed,
                     "skipped": found - processed})
    without_type = found_by_type.get("other", 0)
    if without_type:
        rows.append({"type": "other", "found": without_type, "processed": 0,
                     "skipped": without_type})

    found_files = sum(row["found"] for row in rows)
    processed_files = sum(row["processed"] for row in rows)
    return {
        "foundFiles": found_files,
        "processedFiles": processed_files,
        "skippedFiles": found_files - processed_files,
        "skippedRecords": sum(issue.get("skippedRecords", 0) for issue in issues),
        "measurementPoints": sum(len(values) for values in sdat_data.values()),
        "files": rows,
        "issues": issues,
        "findings": _findings(sdat_data, esl_data, issues, meter_readings or {}),
        "sensors": _sensors(sdat_data, esl_data),
    }


def _sensors(sdat_data, esl_data) -> list[dict]:
    rows = []
    for sensor_id in set(sdat_data) | set(esl_data):
        values = sdat_data.get(sensor_id, [])
        readings = esl_data.get(sensor_id, [])
        # Ohne Messwerte bleibt der Zeitraum der ESL-Ablesungen als Anhaltspunkt.
        days = ([consumption_day_bucket(value.timestamp) for value in values]
                or [reading.start_time.astimezone(LOCAL_TZ).date() for reading in readings])
        rows.append({
            "sensorId": sensor_id,
            "direction": SENSOR_DIRECTIONS.get(sensor_id, "other"),
            "values": len(values),
            "from": min(days).isoformat() if days else "",
            "to": max(days).isoformat() if days else "",
            "eslReadings": len(readings),
        })
    rows.sort(key=lambda row: (DIRECTIONS.index(row["direction"]), row["sensorId"]))
    return rows


def _findings(sdat_data, esl_data, issues: list[dict], meter_readings) -> list[dict]:
    candidates = [*_skipped_meters(issues, esl_data), _single_value_files(sdat_data),
                  _duplicates(sdat_data), _time_change(sdat_data),
                  _factor_three(meter_readings, esl_data)]
    return [finding for finding in candidates if finding]


def _count(amount: int, singular: str, plural: str) -> str:
    return f"{amount} {singular if amount == 1 else plural}"


def _skipped_meters(issues: list[dict], esl_data) -> list[dict]:
    """Ein Hinweis pro übersprungenem Zähler (FA-04).

    Gezählt werden die Dateien, in denen der Zähler vorkommt - nicht übersprungene
    Dateien: liefert dieselbe Datei noch einen brauchbaren Zähler, wird sie gelesen.
    """
    per_meter: dict[str, dict] = {}
    for issue in issues:
        if issue.get("kind") != "meter":
            continue
        entry = per_meter.setdefault(issue.get("meter") or "unbekannt",
                                     {"files": set(), "reason": ""})
        entry["files"].add(issue.get("file", ""))
        entry["reason"] = issue.get("reason", "")

    findings = []
    for meter, entry in sorted(per_meter.items()):
        registers = sorted({row.obis for source in getattr(esl_data, "sources", [])
                            if source.factory_no == meter for row in source.rows if row.obis})
        detail = (f"nur Register {', '.join(registers)}, kein Wirkenergie-Register "
                  "für Bezug oder Einspeisung."
                  if registers and NO_TARIFF_PAIRS in entry["reason"]
                  else f"{entry['reason']}.")
        findings.append({
            "label": "Übersprungen",
            "text": f"Zähler {meter} in {_count(len(entry['files']), 'Datei', 'Dateien')}: {detail}",
        })
    return findings


def _single_value_files(sdat_data) -> dict | None:
    """Dateien mit einem Messwert und ohne Resolution-Angabe; die Auflösung ist geschätzt."""
    lonely = {source.file for source in getattr(sdat_data, "sources", [])
              if source.resolution_unit is None and _spans_one_value(source)}
    if not lonely:
        return None
    only_source_for = sorted(
        sensor_id for sensor_id, values in sdat_data.items()
        if values and all(value.source is not None and value.source.file in lonely
                          for value in values))
    text = (f"{_count(len(lonely), 'sdat-Datei', 'sdat-Dateien')} mit nur einem Messwert "
            "und ohne Angabe zum zeitlichen Abstand.")
    if only_source_for:
        subject = "Einzige Quelle von Sensor" if len(only_source_for) == 1 else "Einzige Quelle der Sensoren"
        text += f" {subject} {', '.join(only_source_for)}."
    return {"label": "Verarbeitet", "text": text}


def _spans_one_value(source) -> bool:
    if source.interval_end is None or source.resolution_minutes <= 0:
        return False
    minutes = (source.interval_end - source.interval_start).total_seconds() / 60
    return minutes <= source.resolution_minutes


def _duplicates(sdat_data) -> dict | None:
    conflicts = getattr(sdat_data, "conflicts", 0)
    if not conflicts:
        return None
    return {
        "label": "Duplikate",
        "text": f"{_count(conflicts, 'Zeitpunkt', 'Zeitpunkte')} mit "
                f"{'widersprüchlichem Wert' if conflicts == 1 else 'widersprüchlichen Werten'}. "
                "Übernommen wurde jeweils der Wert aus der Datei mit dem jüngsten "
                "Erstellungszeitpunkt.",
    }


def _time_change(sdat_data) -> dict | None:
    """Nur vollständig gelesene Umstellungstage; angebrochene Tage sagen nichts aus."""
    counts: set[int] = set()
    for values in sdat_data.values():
        per_day: dict = {}
        for value in values:
            if value.resolution_minutes != 15:
                continue
            day = consumption_day_bucket(value.timestamp)
            per_day[day] = per_day.get(day, 0) + 1
        counts.update(count for day, count in per_day.items()
                      if count == local_day_quarter_hours(day) != QUARTER_HOURS_PER_DAY)
    if not counts:
        return None
    return {
        "label": "Zeitumstellung",
        "text": f"Tage mit {' und '.join(str(count) for count in sorted(counts))} "
                "Viertelstunden erkannt und auf lokaler Mitternacht abgegrenzt.",
    }


def _factor_three(meter_readings, esl_data) -> dict | None:
    """Faktor-3-Abweichung zwischen SDAT-Verbrauch und ESL-Differenz (F14): nur melden."""
    for sensor_id, series in meter_readings.items():
        dates = sorted(esl_data.get(sensor_id, []), key=lambda reading: reading.start_time)
        for first, last in zip(dates, dates[1:]):
            if first.start_time not in series or last.start_time not in series:
                continue
            measured_change = last.start_value - first.start_value
            calculated_change = (series[last.start_time].meter_value
                                 - series[first.start_time].meter_value)
            if measured_change and abs(calculated_change / measured_change - 3) < 0.05:
                return {"label": "Befund",
                        "text": "SDAT-Verbrauch und ESL-Zählerdifferenz weichen bei der "
                                "Testanlage um etwa Faktor 3 ab. Gültige Werte wurden "
                                "unverändert übernommen."}
    return None
