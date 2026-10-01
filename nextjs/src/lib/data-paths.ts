import os from "node:os";
import path from "node:path";

const UUID_RE = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;

export function getDataRoot(): string {
  return process.env.VOLT_TRACE_DATA_DIR ?? path.join(os.tmpdir(), "volt-trace-data");
}

export function getSessionsDir(): string {
  return path.join(getDataRoot(), "_sessions");
}

export function datasetPath(id: string): string {
  if (!UUID_RE.test(id)) throw new Error("Ungültiger Datensatz.");
  return path.join(getDataRoot(), id);
}
