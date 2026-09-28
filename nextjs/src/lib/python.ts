/** Planned Python HTTP contract. All timestamps are ISO-8601 UTC; values are kWh. */
export type Sensor = {
  sensorId: string;
  label: string;
  direction: "consumption" | "feed-in" | "other";
  hasMeterReadings: boolean;
};

export type DataPoint = { ts: string; value: number };
export type SensorSeries = { sensorId: string; data: DataPoint[] };
export type Resolution = "day" | "15min";
export type MeasurementKind = "consumption" | "meter-reading";

export type UploadIssue = { file: string; reason: string; skippedRecords: number };
export type UploadResult = {
  datasetId: string;
  processedFiles: number;
  skippedFiles: number;
  issues: UploadIssue[];
};

export type SeriesQuery = {
  datasetId: string;
  sensorId: string;
  kind: MeasurementKind;
  resolution: Resolution;
  from: string;
  to: string;
};

export type ApiError = { message: string; status?: number };

/** Endpoint paths and payloads to implement in the Python OpenAPI schema. */
export const apiContract = {
  upload: "POST /datasets (multipart/form-data, files[] → UploadResult)",
  sensors: "GET /datasets/{datasetId}/sensors → Sensor[]",
  series: "GET /datasets/{datasetId}/series?… → SensorSeries[]",
  csv: "GET /datasets/{datasetId}/sensors/{sensorId}/export.csv → text/csv",
} as const;
