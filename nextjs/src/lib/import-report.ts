import "server-only";

import { readFile } from "node:fs/promises";
import path from "node:path";

import { datasetIdFromDirectory, isRemotePython } from "@/lib/python-env";
import type { ImportFileType, ImportReport, ImportSensor } from "@/lib/types";

/** Der Bericht entsteht beim Upload; fehlt die Datei, wird er nicht angezeigt. */
export async function readImportReport(directory: string): Promise<ImportReport | null> {
  try {
    if (isRemotePython()) {
      const { remoteReadImportReport } = await import("@/lib/python-remote");
      const raw = await remoteReadImportReport(datasetIdFromDirectory(directory));
      return raw ? JSON.parse(raw) as ImportReport : null;
    }
    return JSON.parse(await readFile(path.join(directory, "import-report.json"), "utf-8")) as ImportReport;
  } catch {
    return null;
  }
}

const number = new Intl.NumberFormat("de-CH");

export const formatCount = (value: number) => number.format(value);

export const FILE_TYPE_LABELS: Record<ImportFileType, string> = {
  sdat: "sdat",
  esl: "ESL",
  other: "Ohne erkannten Typ",
};

export const DIRECTION_LABELS: Record<ImportSensor["direction"], string> = {
  consumption: "Bezug",
  "feed-in": "Einspeisung",
  other: "Weiterer Sensor",
};

/** Die Zeitraumangaben sind schon lokale Datumswerte (YYYY-MM-DD), kein Zeitstempel. */
export function formatLocalDate(date: string): string {
  const [year, month, day] = date.split("-");
  return year && month && day ? `${day}.${month}.${year}` : "";
}

export function formatPeriod(sensor: ImportSensor): string {
  if (!sensor.from) return "–";
  const from = formatLocalDate(sensor.from);
  const to = formatLocalDate(sensor.to);
  return from === to ? from : `${from} – ${to}`;
}
