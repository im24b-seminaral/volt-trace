"""
localtime.py - Lokalzeit-Regeln der Auswertung (F13, NFA-05).

Anzeige und Tagesgrenzen laufen in Europe/Zurich, Daten bleiben in UTC.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Zurich")


def consumption_day_bucket(interval_end_utc: datetime) -> datetime.date:
    """Verbrauchstag aus Intervallende (Europe/Zurich); Mitternacht → Vortag."""
    local_end = interval_end_utc.astimezone(LOCAL_TZ)
    if (
        local_end.hour == 0
        and local_end.minute == 0
        and local_end.second == 0
        and local_end.microsecond == 0
    ):
        return local_end.date() - timedelta(days=1)
    return local_end.date()


def local_day_quarter_hours(day: datetime.date) -> int:
    """Viertelstunden zwischen zwei lokalen Mitternachten: 96, an Umstellungstagen 92 oder 100."""
    start = datetime.combine(day, datetime.min.time(), tzinfo=LOCAL_TZ)
    next_start = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=LOCAL_TZ)
    # Beide Zeitpunkte tragen dieselbe tzinfo; die Differenz gilt erst in UTC.
    span = next_start.astimezone(timezone.utc) - start.astimezone(timezone.utc)
    return int(span.total_seconds() // 900)
