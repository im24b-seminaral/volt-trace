import path from "node:path";

export function getPythonServiceUrl(): string | undefined {
  const raw = process.env.VOLT_TRACE_PYTHON_URL?.trim();
  return raw ? raw.replace(/\/$/, "") : undefined;
}

export function isRemotePython(): boolean {
  return !!getPythonServiceUrl();
}

export function datasetIdFromDirectory(directory: string): string {
  return path.basename(directory);
}
