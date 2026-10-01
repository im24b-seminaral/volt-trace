/**
 * Kopiert ../python nach nextjs/python-runtime für Vercel (Service-Root = nextjs).
 * Turbopack erlaubt kein outputFileTracingIncludes mit ../…
 */
import { cpSync, existsSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const nextjsRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = path.resolve(nextjsRoot, "..", "python");
const target = path.join(nextjsRoot, "python-runtime");

if (!existsSync(source)) {
  console.warn("prepare-python: ../python nicht gefunden, überspringe.");
  process.exit(0);
}

const skip = (p) => {
  const parts = p.split(/[/\\]/);
  return parts.some((part) => part === ".venv" || part === "__pycache__" || part === "tests");
};

rmSync(target, { recursive: true, force: true });
cpSync(source, target, {
  recursive: true,
  filter: (src) => !skip(src),
});
console.log(`prepare-python: ${source} → ${target}`);
