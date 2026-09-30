"use server";

import { randomUUID } from "node:crypto";
import { mkdir, writeFile, rm } from "node:fs/promises";
import path from "node:path";
import { redirect } from "next/navigation";
import { datasetPath, runPython } from "@/lib/python";
import type { ImportReport } from "@/lib/types";

function safeUploadPath(value: string): string {
  const parts = value.replaceAll("\\", "/").split("/");
  if (!parts.length || parts.some((part) => !part || part === "." || part === ".."
    || part.includes(":") || part.includes("\0"))) {
    throw new Error("Ungültiger Dateipfad im Upload.");
  }
  return path.join(...parts);
}

export async function uploadDataset(_previous: string, form: FormData): Promise<string> {
  const selectedFiles = form.getAll("files").filter((file): file is File => file instanceof File && !!file.name);
  const folderFiles = form.getAll("folder").filter((file): file is File => file instanceof File && !!file.name);
  const folderPaths = form.getAll("folderPath").map(String);
  if (!selectedFiles.length && !folderFiles.length) return "Bitte XML-/ZIP-Dateien oder einen Ordner auswählen.";
  const id = randomUUID();
  const destination = datasetPath(id);
  const raw = destination + "_raw";
  try {
    await mkdir(raw, { recursive: true });
    const names = new Set<string>();
    for (const [index, file] of [...selectedFiles, ...folderFiles].entries()) {
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
    }
    const result = JSON.parse(await runPython("sort-files", raw, destination)) as ImportReport;
    if (result.processedFiles === 0) {
      await rm(destination, { recursive: true, force: true });
      return result.issues[0]
        ? `Keine XML-Datei eingelesen: ${result.issues[0].file}: ${result.issues[0].reason}`
        : "Keine verwendbaren XML-Dateien gefunden.";
    }
    await writeFile(path.join(destination, "import-report.json"), JSON.stringify(result), "utf-8");
  } catch (error) {
    console.error(error);
    await rm(destination, { recursive: true, force: true });
    return error instanceof Error ? error.message : "Upload fehlgeschlagen. Bitte erneut versuchen.";
  } finally {
    await rm(raw, { recursive: true, force: true });
  }
  redirect(`/?dataset=${id}`);
}
