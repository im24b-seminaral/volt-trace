"""Gemeinsame Rundung für kWh-Werte (NFA-04)."""

KWH_DECIMALS = 4


def round_kwh(value: float) -> float:
    return round(value, KWH_DECIMALS)


def sum_kwh(values) -> float:
    return round_kwh(sum(values))
