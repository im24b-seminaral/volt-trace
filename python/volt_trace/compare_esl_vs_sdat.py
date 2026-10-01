from typing import List, Dict

# pyrefly: ignore [missing-import]
from volt_trace.sdat import (
    MeasuredValue,
    load_sdat_folder,
    remove_duplicates,
    sort_measured_values_by_time,
)

# pyrefly: ignore [missing-import]
from volt_trace.esl import EslMeterReading, load_esl_folder

# pyrefly: ignore [missing-import]
from volt_trace.analysis import DATA_DIR

def compare_esl_sdat(
    messwerte: List[MeasuredValue],
    esl_werte: List[EslMeterReading],
    ) -> Dict[str, List[float]]:
    messwerte = remove_duplicates(sort_measured_values_by_time(messwerte))
    esl_sorted = sorted(esl_werte, key=lambda z: z.start_time)
    results = []
    for a, b in zip(esl_sorted, esl_sorted[1:]):
        esl_diff = b.start_value - a.start_value
        # SDAT-Zeitstempel bezeichnen das Intervallende: (Beginn, Ende].
        sdat_in_range = [mv for mv in messwerte if a.start_time < mv.timestamp <= b.start_time]
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
    sdat = load_sdat_folder(DATA_DIR / "SDAT-Files")
    esl = load_esl_folder(DATA_DIR / "ESL-Files")

    comp = compare_esl_sdat(sdat["ID742"], esl["ID742"])
    for entry in comp:
        print(entry["von"].date(), "->", entry["bis"].date(),
              "ESL:", entry["esl_diff"], "SDAT:", entry["sdat_summe"],
              "Verhältnis:", entry["verhaeltnis"])
