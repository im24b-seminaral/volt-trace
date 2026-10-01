import "server-only";

import { PYTHON_TIMEOUT_MS } from "@/lib/constants";
import { datasetIdFromDirectory, getPythonServiceUrl } from "@/lib/python-env";
import type { PythonProgress } from "@/lib/python";

function serviceUrl(pathname: string): URL {
  const base = getPythonServiceUrl();
  if (!base) throw new Error("Python-Service nicht konfiguriert.");
  return new URL(pathname, `${base}/`);
}

async function readNdjsonResponse(
  response: Response,
  onProgress: (event: PythonProgress) => void,
): Promise<string> {
  if (!response.body) throw new Error("Leere Antwort vom Python-Service.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let lastReport = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newline = buffer.indexOf("\n");
    while (newline >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (!line) {
        newline = buffer.indexOf("\n");
        continue;
      }
      const event = JSON.parse(line) as Record<string, unknown>;
      if (typeof event.error === "string") throw new Error(event.error);
      if (typeof event.step === "string") onProgress(event as PythonProgress);
      else if (typeof event.processedFiles === "number") lastReport = line;
      newline = buffer.indexOf("\n");
    }
  }
  const tail = buffer.trim();
  if (tail) {
    const event = JSON.parse(tail) as Record<string, unknown>;
    if (typeof event.error === "string") throw new Error(event.error);
    if (typeof event.step === "string") onProgress(event as PythonProgress);
    else if (typeof event.processedFiles === "number") lastReport = tail;
  }
  if (!lastReport) throw new Error("Python-Service hat keinen Importbericht geliefert.");
  return lastReport;
}

export async function remoteImportDataset(
  datasetId: string,
  form: FormData,
  onProgress: (event: PythonProgress) => void,
  signal?: AbortSignal,
): Promise<string> {
  const url = serviceUrl(`/v1/datasets/${datasetId}/import`);
  const response = await fetch(url, { method: "POST", body: form, signal });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Python-Service antwortete mit ${response.status}.`);
  }
  return readNdjsonResponse(response, onProgress);
}

export async function remoteDeleteDataset(datasetId: string): Promise<void> {
  const response = await fetch(serviceUrl(`/v1/datasets/${datasetId}`), { method: "DELETE" });
  if (!response.ok && response.status !== 404) {
    throw new Error(`Datensatz konnte nicht gelöscht werden (${response.status}).`);
  }
}

export async function remoteReadImportReport(datasetId: string): Promise<string> {
  const response = await fetch(serviceUrl(`/v1/datasets/${datasetId}/import-report`), {
    cache: "no-store",
  });
  if (response.status === 404) return "";
  if (!response.ok) throw new Error(`Importbericht nicht lesbar (${response.status}).`);
  return response.text();
}

export async function remoteRunPython(command: string, directory: string, ...args: string[]): Promise<string> {
  const datasetId = datasetIdFromDirectory(directory);
  const base = getPythonServiceUrl();
  if (!base) throw new Error("Python-Service nicht konfiguriert.");
  const timeout = AbortSignal.timeout(PYTHON_TIMEOUT_MS);

  if (command === "sensors") {
    const response = await fetch(serviceUrl(`/v1/datasets/${datasetId}/sensors`), { signal: timeout });
    if (!response.ok) throw remoteError(response);
    return response.text();
  }

  if (command === "series") {
    const [sensorId, kind, resolution, fromUtc, toUtc] = args;
    const url = serviceUrl(`/v1/datasets/${datasetId}/series`);
    url.searchParams.set("sensor_id", sensorId);
    url.searchParams.set("kind", kind);
    url.searchParams.set("resolution", resolution);
    if (fromUtc) url.searchParams.set("from_str", fromUtc);
    if (toUtc) url.searchParams.set("to_str", toUtc);
    const response = await fetch(url, { signal: timeout });
    if (!response.ok) throw remoteError(response);
    return response.text();
  }

  if (command === "export") {
    const [sensorId, kind, fileFormat = "csv"] = args;
    const url = serviceUrl(`/v1/datasets/${datasetId}/export/${encodeURIComponent(sensorId)}`);
    url.searchParams.set("kind", kind);
    url.searchParams.set("file_format", fileFormat);
    const response = await fetch(url, { signal: timeout });
    if (!response.ok) throw remoteError(response, true);
    return new TextDecoder().decode(await response.arrayBuffer());
  }

  throw new Error(`Unbekanntes Python-Kommando: ${command}`);
}

function remoteError(response: Response, exportKind = false): Error & { code?: number } {
  const failure = new Error(
    exportKind && response.status === 404
      ? "Keine Daten für diesen Export vorhanden."
      : `Python-Service antwortete mit ${response.status}.`,
  ) as Error & { code?: number };
  if (exportKind && response.status === 404) failure.code = 1;
  return failure;
}
