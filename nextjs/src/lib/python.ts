import "server-only";
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);
const pythonDir = path.resolve(process.cwd(), "../python");
export const dataDir = path.resolve(process.cwd(), "data");
const venv = path.join(pythonDir, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const python = existsSync(venv) ? venv : process.platform === "win32" ? "python" : "python3";

export function datasetPath(id: string) {
  if (!/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(id)) throw new Error("Ungültiger Datensatz.");
  return path.join(dataDir, id);
}

export async function runPython(command: string, ...args: string[]) {
  const { stdout } = await run(python, ["-m", "volt_trace.cli", command, ...args], {
    cwd: pythonDir, maxBuffer: 32 * 1024 * 1024,
  });
  return stdout;
}
