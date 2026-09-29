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

const API_BASE = "/api";

export async function uploadDataset(files: File[]): Promise<UploadResult> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const res = await fetch(`${API_BASE}/datasets`, { method: "POST", body: formData });
  if (!res.ok) throw new Error(`Upload fehlgeschlagen: ${res.status}`);
  return res.json();
}

export async function getSensors(datasetId: string): Promise<Sensor[]> {
  const res = await fetch(`${API_BASE}/datasets/${encodeURIComponent(datasetId)}/sensors`);
  if (!res.ok) throw new Error(`Sensors laden fehlgeschlagen: ${res.status}`);
  return res.json();
}

export async function getSeries(query: SeriesQuery): Promise<SensorSeries[]> {
  const params = new URLSearchParams({
    sensorId: query.sensorId,
    kind: query.kind,
    resolution: query.resolution,
    from: query.from,
    to: query.to,
  });
  const res = await fetch(`${API_BASE}/datasets/${encodeURIComponent(query.datasetId)}/series?${params}`);
  if (!res.ok) throw new Error(`Series laden fehlgeschlagen: ${res.status}`);
  return res.json();
}

export function getExportCsvUrl(datasetId: string, sensorId: string): string {
  return `${API_BASE}/datasets/${encodeURIComponent(datasetId)}/sensors/${encodeURIComponent(sensorId)}/export.csv`;
}
