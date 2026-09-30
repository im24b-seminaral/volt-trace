export type Sensor = { sensorId: string; label: string; hasConsumption: boolean; hasMeterReadings: boolean };
export type DataPoint = { ts: string; value: number };
export type SensorSeries = { sensorId: string; data: DataPoint[] };
export type ImportIssue = {
  file: string;
  kind: "file" | "record" | "meter";
  reason: string;
  skippedRecords: number;
  meter?: string;
  obis?: string | null;
  status?: string;
};
export type ImportReport = {
  foundFiles: number;
  processedFiles: number;
  skippedFiles: number;
  skippedRecords: number;
  issues: ImportIssue[];
  findings: string[];
};
