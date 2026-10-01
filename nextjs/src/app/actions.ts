"use server";

import { randomUUID } from "node:crypto";
import { mkdir, writeFile, rm } from "node:fs/promises";
import path from "node:path";
import { redirect } from "next/navigation";
import { datasetPath, runPython } from "@/lib/python";
import { deleteDataset, endSession, getOrCreateSession, registerDataset } from "@/lib/session";

export async function clearSession(): Promise<void> {
  await endSession();
}

export async function uploadDataset(_previous: string, form: FormData): Promise<string> {
  const files = [...form.getAll("files"), ...form.getAll("folder")]
    .filter((file): file is File => file instanceof File && file.size > 0 && file.name.toLowerCase().endsWith(".xml"));
  if (!files.length) return "Bitte XML-Dateien auswählen.";
  const sessionId = await getOrCreateSession();
  const id = randomUUID();
  const destination = datasetPath(id);
  const raw = destination + "_raw";
  let skipped = 0;
  let uploadOk = false;
  try {
    await mkdir(raw, { recursive: true });
    const names = new Set<string>();
    for (const file of files) {
      const base = file.name.replace(/\\/g, "/").split("/").pop()!;
      let name = base;
      let suffix = 1;
      while (names.has(name.toLowerCase())) name = `${path.parse(base).name}_${suffix++}${path.extname(base)}`;
      names.add(name.toLowerCase());
      await writeFile(path.join(raw, name), Buffer.from(await file.arrayBuffer()));
    }
    const result = JSON.parse(await runPython("sort-files", raw, destination));
    skipped = result.skippedFiles;
    await registerDataset(sessionId, id);
    uploadOk = true;
  } catch (error) {
    console.error(error);
    return "Upload fehlgeschlagen. Bitte erneut versuchen.";
  } finally {
    await rm(raw, { recursive: true, force: true });
    if (!uploadOk) await deleteDataset(id);
  }
  redirect(`/?dataset=${id}${skipped ? `&skipped=${skipped}` : ""}`);
}
