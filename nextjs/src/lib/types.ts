export type Sensor = { sensorId: string; label: string; hasConsumption: boolean; hasMeterReadings: boolean; consumptionDates: string[]; meterReadingDates: string[] };
export type DataPoint = { ts: string; value: number };
export type SensorSeries = { sensorId: string; data: DataPoint[] };
export type ImportIssue = {
  file: string;
  kind: "file" | "record" | "meter";
  reason: string;
  skippedRecords: number;
  /** Nur bei Dateien, die ein Loader nicht lesen konnte. */
  type?: ImportFileType;
  meter?: string;
  obis?: string | null;
  status?: string;
};
/** "other": Datei ohne erkannten Typ, etwa kein XML oder unbekanntes Format. */
export type ImportFileType = "sdat" | "esl" | "other";
export type ImportFileCount = { type: ImportFileType; found: number; processed: number; skipped: number };
/** label trägt das Stichwort des Hinweises, etwa "Duplikate". */
export type ImportFinding = { label: string; text: string };
export type ImportSensor = {
  sensorId: string;
  direction: "consumption" | "feed-in" | "other";
  values: number;
  from: string;
  to: string;
  eslReadings: number;
};
export type ImportReport = {
  foundFiles: number;
  processedFiles: number;
  skippedFiles: number;
  skippedRecords: number;
  measurementPoints: number;
  files: ImportFileCount[];
  issues: ImportIssue[];
  findings: ImportFinding[];
  sensors: ImportSensor[];
};
