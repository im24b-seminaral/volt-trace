import "server-only";
import { execFile, spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createInterface } from "node:readline";
import path from "node:path";
import { promisify } from "node:util";

import { PYTHON_TIMEOUT_MS } from "@/lib/constants";
import { datasetPath, getDataRoot } from "@/lib/runtime-data";

const run = promisify(execFile);
const pythonDir = path.resolve(process.cwd(), "../python");
/** @deprecated Verwende getDataRoot(); Laufzeitdaten liegen nicht mehr unter nextjs/data. */
export const dataDir = getDataRoot();
const venv = path.join(pythonDir, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = existsSync(venv) ? venv : process.platform === "win32" ? "python" : "python3";

export { datasetPath };

export type PythonProgress = { step: string; done?: number; total?: number };

const PROGRESS_PREFIX = "@progress ";

/**
 * Wie runPython, meldet aber die @progress-Zeilen, die das CLI auf stderr
 * schreibt, während der Prozess läuft. execFile puffert bis zum Ende und
 * taugt dafür nicht.
 */
export function runPythonProgress(
  onProgress: (event: PythonProgress) => void,
  command: string,
  ...args: string[]
): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(python, ["-m", "volt_trace.cli", command, ...args], {
      cwd: pythonDir, env: { ...process.env, VOLT_TRACE_PROGRESS: "1" },
    });
    let stdout = "";
    let lastError = "";
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error("Die Python-Verarbeitung hat das Zeitlimit überschritten. Bitte erneut versuchen."));
    }, PYTHON_TIMEOUT_MS);

    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => { stdout += chunk; });
    createInterface({ input: child.stderr }).on("line", (line) => {
      if (line.startsWith(PROGRESS_PREFIX)) onProgress(JSON.parse(line.slice(PROGRESS_PREFIX.length)));
      else if (line.trim()) lastError = line;
    });
    child.on("error", (cause) => {
      clearTimeout(timer);
      reject(new Error(`Python-Verarbeitung fehlgeschlagen: ${cause.message}`));
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) resolve(stdout);
      else reject(new Error(`Python-Verarbeitung fehlgeschlagen: ${lastError || `Exit-Code ${code}`}`));
    });
  });
}

export async function runPython(command: string, ...args: string[]) {
  try {
    const { stdout } = await run(python, ["-m", "volt_trace.cli", command, ...args], {
      cwd: pythonDir, maxBuffer: 32 * 1024 * 1024, timeout: PYTHON_TIMEOUT_MS,
    });
    return stdout;
  } catch (cause) {
    const failure = cause as Error & { killed?: boolean; code?: string | number; stderr?: string };
    if (failure.killed || failure.code === "ETIMEDOUT") {
      throw new Error("Die Python-Verarbeitung hat das Zeitlimit überschritten. Bitte erneut versuchen.");
    }
    const detail = failure.stderr?.trim().split(/\r?\n/).at(-1) || failure.message;
    throw new Error(`Python-Verarbeitung fehlgeschlagen: ${detail}`);
  }
}
