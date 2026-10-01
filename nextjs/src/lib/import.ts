import "server-only";

import { randomUUID } from "node:crypto";
import { mkdir, writeFile, rm } from "node:fs/promises";
import path from "node:path";

import { datasetPath, runPythonProgress, type PythonProgress } from "@/lib/python";
import { deleteDataset, getOrCreateSession, registerDataset } from "@/lib/session";
import type { ImportReport } from "@/lib/types";

export type ImportResult = { datasetId: string } | { error: string };

function safeUploadPath(value: string): string {
  const parts = value.replaceAll("\\", "/").split("/");
  if (!parts.length || parts.some((part) => !part || part === "." || part === ".."
    || part.includes(":") || part.includes("\0"))) {
    throw new Error("Ungültiger Dateipfad im Upload.");
  }
  return path.join(...parts);
}

/**
 * Nimmt die hochgeladenen Dateien entgegen, lässt sie von der Python-Pipeline
 * einlesen und meldet dabei jeden Schritt. Gibt entweder die Datensatz-ID oder
 * eine Meldung für die Oberfläche zurück.
 */
export async function importUpload(
  form: FormData,
  onProgress: (event: PythonProgress) => void = () => {},
): Promise<ImportResult> {
  const selectedFiles = form.getAll("files").filter((file): file is File => file instanceof File && !!file.name);
  const folderFiles = form.getAll("folder").filter((file): file is File => file instanceof File && !!file.name);
  const folderPaths = form.getAll("folderPath").map(String);
  if (!selectedFiles.length && !folderFiles.length) return { error: "Bitte XML-/ZIP-Dateien oder einen Ordner auswählen." };

  const sessionId = await getOrCreateSession();
  const id = randomUUID();
  const destination = datasetPath(id);
  const raw = destination + "_raw";
  let uploadOk = false;
  try {
    await mkdir(raw, { recursive: true });
    const names = new Set<string>();
    const incoming = [...selectedFiles, ...folderFiles];
    onProgress({ step: "write", done: 0, total: incoming.length });
    for (const [index, file] of incoming.entries()) {
      const isFolder = index >= selectedFiles.length;
      const relative = safeUploadPath(isFolder
        ? folderPaths[index - selectedFiles.length] || file.name
        : file.name);
      const original = path.join(isFolder ? "folder" : "files", relative);
      let name = original;
      let suffix = 1;
      while (names.has(name.toLowerCase())) {
        const parsed = path.parse(original);
        name = path.join(parsed.dir, `${parsed.name}_${suffix++}${parsed.ext}`);
      }
      names.add(name.toLowerCase());
      const target = path.join(raw, name);
      await mkdir(path.dirname(target), { recursive: true });
      await writeFile(target, Buffer.from(await file.arrayBuffer()));
      onProgress({ step: "write", done: index + 1, total: incoming.length });
    }
    const result = JSON.parse(await runPythonProgress(onProgress, "sort-files", raw, destination)) as ImportReport;
    if (result.processedFiles === 0) {
      await rm(destination, { recursive: true, force: true });
      return {
        error: result.issues[0]
          ? `Keine XML-Datei eingelesen: ${result.issues[0].file}: ${result.issues[0].reason}`
          : "Keine verwendbaren XML-Dateien gefunden.",
      };
    }
    await writeFile(path.join(destination, "import-report.json"), JSON.stringify(result), "utf-8");
    await registerDataset(sessionId, id);
    uploadOk = true;
  } catch (error) {
    console.error(error);
    await rm(destination, { recursive: true, force: true });
    return { error: error instanceof Error ? error.message : "Upload fehlgeschlagen. Bitte erneut versuchen." };
  } finally {
    await rm(raw, { recursive: true, force: true });
    if (!uploadOk) await deleteDataset(id);
  }
  return { datasetId: id };
}
