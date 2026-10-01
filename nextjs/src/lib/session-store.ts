import { mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";

import { datasetPath, getDataRoot, getSessionsDir } from "@/lib/data-paths";
import { isRemotePython } from "@/lib/python-env";

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
  return 2 * 60 * 1000;
}

function sessionFilePath(sessionId: string): string {
  if (!UUID_RE.test(sessionId)) throw new Error("Ungültige Sitzung.");
  return path.join(getSessionsDir(), `${sessionId}.json`);
}

async function ensureSessionsDir(): Promise<void> {
  await mkdir(getSessionsDir(), { recursive: true });
}

const sessionLocks = new Map<string, Promise<void>>();

async function withSessionLock<T>(sessionId: string, work: () => Promise<T>): Promise<T> {
  const previous = sessionLocks.get(sessionId) ?? Promise.resolve();
  let release!: () => void;
  const current = new Promise<void>((resolve) => { release = resolve; });
  sessionLocks.set(sessionId, current);
  await previous;
  try {
    return await work();
  } finally {
    release();
    if (sessionLocks.get(sessionId) === current) sessionLocks.delete(sessionId);
  }
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
  return withSessionLock(sessionId, async () => {
    const now = Date.now();
    const existing = await loadSession(sessionId);
    if (existing && Date.parse(existing.expiresAt) <= now) {
      await removeSessionData(sessionId, existing);
    }
    const record: SessionRecord = {
      datasetIds: existing && Date.parse(existing.expiresAt) > now ? existing.datasetIds : [],
      lastSeen: new Date(now).toISOString(),
      expiresAt: new Date(now + getSessionIdleTtlMs()).toISOString(),
    };
    await saveSession(sessionId, record);
    return record;
  });
}

export async function registerDataset(sessionId: string, datasetId: string): Promise<void> {
  await withSessionLock(sessionId, async () => {
    const record = await loadSession(sessionId);
    if (!record || Date.parse(record.expiresAt) <= Date.now()) {
      throw new Error("Sitzung abgelaufen. Bitte erneut hochladen.");
    }
    if (!record.datasetIds.includes(datasetId)) {
      record.datasetIds.push(datasetId);
      await saveSession(sessionId, record);
    }
  });
}

export async function isDatasetOwned(sessionId: string, datasetId: string): Promise<boolean> {
  const record = await loadSession(sessionId);
  return !!record && Date.parse(record.expiresAt) > Date.now() && record.datasetIds.includes(datasetId);
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
  if (isRemotePython()) {
    const { remoteDeleteDataset } = await import("@/lib/python-remote");
    await remoteDeleteDataset(datasetId);
    return;
  }
  await rm(datasetPath(datasetId), { recursive: true, force: true });
}

async function removeSessionData(sessionId: string, record: SessionRecord | null): Promise<void> {
  await rm(sessionFilePath(sessionId), { force: true });
  if (record) {
    for (const id of record.datasetIds) {
      await deleteDataset(id);
    }
  }
}

export async function destroySession(sessionId: string): Promise<void> {
  await withSessionLock(sessionId, async () => {
    await removeSessionData(sessionId, await loadSession(sessionId));
  });
}

export async function purgeExpiredSessions(): Promise<number> {
  await ensureSessionsDir();
  let removed = 0;
  for (const name of await readdir(getSessionsDir())) {
    if (!name.endsWith(".json")) continue;
    const sessionId = name.slice(0, -".json".length);
    if (!UUID_RE.test(sessionId)) continue;
    removed += await withSessionLock(sessionId, async () => {
      const record = await loadSession(sessionId);
      if (!record || Date.parse(record.expiresAt) > Date.now()) return 0;
      await removeSessionData(sessionId, record);
      return 1;
    });
  }
  return removed;
}

export async function purgeOrphanedUploads(): Promise<void> {
  const root = getDataRoot();
  await ensureSessionsDir();
  const owned = new Set<string>();
  for (const name of await readdir(getSessionsDir())) {
    if (!name.endsWith(".json")) continue;
    const record = await loadSession(name.slice(0, -5));
    for (const id of record?.datasetIds ?? []) owned.add(id);
  }
  const cutoff = Date.now() - 5 * 60_000;
  for (const entry of await readdir(root, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const id = entry.name.endsWith("_raw") ? entry.name.slice(0, -4) : entry.name;
    if (!UUID_RE.test(id) || (entry.name === id && owned.has(id))) continue;
    const directory = path.join(root, entry.name);
    try {
      if ((await stat(directory)).mtimeMs < cutoff) {
        await rm(directory, { recursive: true, force: true });
      }
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
}

let lastPurgeAt = 0;
const PURGE_INTERVAL_MS = 60_000;

export async function maybePurgeExpiredThrottled(): Promise<void> {
  const now = Date.now();
  if (now - lastPurgeAt < PURGE_INTERVAL_MS) return;
  lastPurgeAt = now;
  await purgeExpiredSessions();
}
