import type { Sensor } from "@/lib/types";

export function isDateInput(value: string): boolean {
  const date = new Date(`${value}T00:00:00Z`);
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

/** Hat dieser Sensor Daten für diese Diagrammart? */
export function hasDataFor(sensor: Sensor, kind: string): boolean {
  return kind === "consumption"
    ? sensor.hasConsumption && sensor.consumptionDates.length > 0
    : sensor.hasMeterReadings && sensor.meterReadingDates.length > 0;
}

/** FA-03: jeder importierte Sensor bleibt wählbar, auch ohne ESL-Daten. */
export function importedSensors(sensors: Sensor[]): Sensor[] {
  return sensors.filter((sensor) =>
    hasDataFor(sensor, "consumption") || hasDataFor(sensor, "meter-reading"));
}

/** Nur die Sensoren, die für diese Diagrammart etwas anzuzeigen haben. */
export function sensorsFor(sensors: Sensor[], kind: string): Sensor[] {
  return sensors.filter((sensor) => hasDataFor(sensor, kind));
}

export function sensorDateRange(sensors: Sensor[], kind: string) {
  const dates = sensors.flatMap((sensor) => kind === "consumption" ? sensor.consumptionDates : sensor.meterReadingDates).sort();
  return { first: dates[0] ?? "", last: dates.at(-1) ?? "" };
}

export function dateRangeError(from: string, to: string, first: string, last: string): string {
  if (!isDateInput(from) || !isDateInput(to)) return "Bitte zwei gültige Daten eingeben.";
  if (from > to) return "Von darf nicht nach Bis liegen.";
  if ((first && from < first) || (last && to > last)) return "Bitte einen Zeitraum innerhalb der vorhandenen Daten wählen.";
  return "";
}

export function rangeDays(from: string, to: string): number {
  return isDateInput(from) && isDateInput(to) ? (Date.parse(to) - Date.parse(from)) / 86400000 + 1 : 0;
}

/** Longer 15-minute series are too dense for the chart. */
export const maxDetailDays = 7;

/** Only for meter-reading labels; ESL readings are never aggregated. */
export function rangeResolution(from: string, to: string): "15min" | "day" {
  const days = rangeDays(from, to);
  return days > 0 && days <= maxDetailDays ? "15min" : "day";
}

/** FA-08: consumption defaults to daily values; 15-minute detail only on request and up to maxDetailDays. */
export function parseResolution(value: string, from: string, to: string): "15min" | "day" {
  return value === "15min" && rangeResolution(from, to) === "15min" ? "15min" : "day";
}

export const datePresets = ["7 Tage", "Monat", "Jahr", "Alles"] as const;
export type DatePreset = typeof datePresets[number];

/** Inclusive calendar ranges, ending on Bis; clamp shortcuts to available data. */
export function presetRange(preset: DatePreset, end: string, first: string, last: string) {
  if (preset === "Alles") return { from: first, to: last };
  const to = isDateInput(end) ? (end < first ? first : end > last ? last : end) : last;
  const date = new Date(`${to}T00:00:00Z`);
  if (!Number.isFinite(date.getTime())) return { from: first, to: last };
  if (preset === "7 Tage") date.setUTCDate(date.getUTCDate() - 6);
  else {
    const day = date.getUTCDate();
    date.setUTCDate(1);
    date.setUTCMonth(date.getUTCMonth() - (preset === "Monat" ? 1 : 12));
    const monthEnd = new Date(date);
    monthEnd.setUTCMonth(monthEnd.getUTCMonth() + 1, 0);
    date.setUTCDate(Math.min(day, monthEnd.getUTCDate()) + 1);
  }
  const from = date.toISOString().slice(0, 10);
  return { from: from < first ? first : from, to };
}

export function sensorColor(id: string): string {
  // Keep each sensor's colour when another sensor is deselected.
  const number = Number(id.replace(/\D/g, "")) || 0;
  return `var(--chart-${number % 5 + 1})`;
}
