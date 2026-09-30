import "server-only";
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

import { datasetPath, getDataRoot } from "@/lib/runtime-data";

const run = promisify(execFile);
const pythonDir = path.resolve(process.cwd(), "../python");
/** @deprecated Verwende getDataRoot(); Laufzeitdaten liegen nicht mehr unter nextjs/data. */
export const dataDir = getDataRoot();
const venv = path.join(pythonDir, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = existsSync(venv) ? venv : process.platform === "win32" ? "python" : "python3";

export { datasetPath };

export async function runPython(command: string, ...args: string[]) {
  try {
    const { stdout } = await run(python, ["-m", "volt_trace.cli", command, ...args], {
      cwd: pythonDir, maxBuffer: 32 * 1024 * 1024, timeout: 180_000,
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
