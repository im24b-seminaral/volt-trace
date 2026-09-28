from typing import List, Dict
from datetime import datetime
from pathlib import Path

# pyrefly: ignore [missing-import]
from sdat import MeasuredValue, load_sdat_folder

# pyrefly: ignore [missing-import]
from esl import EslMeterReading, load_esl_folder

def sort_measured_values_by_time(measured_values: List[MeasuredValue]) -> List[MeasuredValue]:
    measured_values.sort(key=lambda value: value.timestamp)
    return measured_values

def remove_duplicates(measured_values: List[MeasuredValue]) -> List[MeasuredValue]:
    unique_measured_values: List[MeasuredValue] = []
    seen_timestamps = set()
    for measured_value in measured_values:
        if measured_value.timestamp not in seen_timestamps:
            unique_measured_values.append(measured_value)
            seen_timestamps.add(measured_value.timestamp)
    return unique_measured_values

def compare_esl_sdat(
    messwerte: List[MeasuredValue],
    esl_werte: List[EslMeterReading],
    ) -> Dict[str, List[float]]:
    messwerte = remove_duplicates(sort_measured_values_by_time(messwerte))
    esl_sorted = sorted(esl_werte, key=lambda z: z.start_time)
    results = []
    for a, b in zip(esl_sorted, esl_sorted[1:]):
        esl_diff = b.start_value - a.start_value
        sdat_in_range = [mv for mv in messwerte if a.start_time <= mv.timestamp < b.start_time]
        sdat_summe = sum(mv.volume for mv in sdat_in_range)

        results.append({
            "von": a.start_time,
            "bis": b.start_time,
            "esl_diff": esl_diff,
            "sdat_summe": sdat_summe,
            "anzahl_messwerte": len(sdat_in_range),
            "verhaeltnis": sdat_summe / esl_diff if esl_diff else None,
        })
    return results

if __name__ == "__main__":
    sdat = load_sdat_folder(Path("C:\\volt-trace\\XML-Files\\SDAT-Files"))
    esl = load_esl_folder(Path("C:\\volt-trace\\XML-Files\\ESL-Files"))

    comp = compare_esl_sdat(sdat["ID742"], esl["ID742"])
    for entry in comp:
        print(entry["von"].date(), "->", entry["bis"].date(),
              "ESL:", entry["esl_diff"], "SDAT:", entry["sdat_summe"],
              "Verhältnis:", entry["verhaeltnis"])