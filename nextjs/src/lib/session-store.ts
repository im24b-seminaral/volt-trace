import { mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";

import { datasetPath, getSessionsDir } from "@/lib/data-paths";

const UUID_RE = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;

export type SessionRecord = {
  datasetIds: string[];
  lastSeen: string;
  expiresAt: string;
};

export class DatasetAccessError extends Error {
  constructor(message = "Datensatz nicht verfügbar.") {
    super(message);
    this.name = "DatasetAccessError";
  }
}

export function getSessionIdleTtlMs(): number {
  const raw = process.env.SESSION_IDLE_TTL_MS;
  if (raw) {
    const parsed = Number(raw);
    if (Number.isFinite(parsed) && parsed > 0) return parsed;
  }
  return 4 * 60 * 60 * 1000;
}

function sessionFilePath(sessionId: string): string {
  if (!UUID_RE.test(sessionId)) throw new Error("Ungültige Sitzung.");
  return path.join(getSessionsDir(), `${sessionId}.json`);
}

async function ensureSessionsDir(): Promise<void> {
  await mkdir(getSessionsDir(), { recursive: true });
}

export async function loadSession(sessionId: string): Promise<SessionRecord | null> {
  try {
    const raw = await readFile(sessionFilePath(sessionId), "utf8");
    return JSON.parse(raw) as SessionRecord;
  } catch {
    return null;
  }
}

export async function saveSession(sessionId: string, record: SessionRecord): Promise<void> {
  await ensureSessionsDir();
  await writeFile(sessionFilePath(sessionId), JSON.stringify(record), "utf8");
}

export async function touchSession(sessionId: string): Promise<SessionRecord> {
  const now = Date.now();
  const expiresAt = new Date(now + getSessionIdleTtlMs()).toISOString();
  const existing = await loadSession(sessionId);
  const record: SessionRecord = {
    datasetIds: existing?.datasetIds ?? [],
    lastSeen: new Date(now).toISOString(),
    expiresAt,
  };
  await saveSession(sessionId, record);
  return record;
}

export async function registerDataset(sessionId: string, datasetId: string): Promise<void> {
  const record = await touchSession(sessionId);
  if (!record.datasetIds.includes(datasetId)) {
    record.datasetIds.push(datasetId);
    await saveSession(sessionId, record);
  }
}

export async function isDatasetOwned(sessionId: string, datasetId: string): Promise<boolean> {
  const record = await loadSession(sessionId);
  return record?.datasetIds.includes(datasetId) ?? false;
}

export async function assertDatasetOwned(sessionId: string, datasetId: string): Promise<void> {
  if (!(await isDatasetOwned(sessionId, datasetId))) {
    throw new DatasetAccessError();
  }
}

export async function resolveOwnedDatasetPath(sessionId: string, datasetId: string): Promise<string> {
  await assertDatasetOwned(sessionId, datasetId);
  return datasetPath(datasetId);
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await rm(datasetPath(datasetId), { recursive: true, force: true });
}

export async function destroySession(sessionId: string): Promise<void> {
  const record = await loadSession(sessionId);
  if (record) {
    for (const id of record.datasetIds) {
      await deleteDataset(id);
    }
  }
  await rm(sessionFilePath(sessionId), { force: true });
}

export async function purgeExpiredSessions(): Promise<number> {
  await ensureSessionsDir();
  const now = Date.now();
  let removed = 0;
  for (const name of await readdir(getSessionsDir())) {
    if (!name.endsWith(".json")) continue;
    const sessionId = name.slice(0, -".json".length);
    const record = await loadSession(sessionId);
    if (!record) continue;
    if (Date.parse(record.expiresAt) < now) {
      await destroySession(sessionId);
      removed += 1;
    }
  }
  return removed;
}

let lastPurgeAt = 0;
const PURGE_INTERVAL_MS = 60_000;

export async function maybePurgeExpiredThrottled(): Promise<void> {
  const now = Date.now();
  if (now - lastPurgeAt < PURGE_INTERVAL_MS) return;
  lastPurgeAt = now;
  await purgeExpiredSessions();
}
