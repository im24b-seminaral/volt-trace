import assert from "node:assert/strict";
import { mkdir, rm, utimes, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, it } from "node:test";
import { randomUUID } from "node:crypto";

import { existsSync } from "node:fs";

import { datasetPath } from "./data-paths";
import {
  assertDatasetOwned,
  DatasetAccessError,
  deleteDataset,
  destroySession,
  isDatasetOwned,
  purgeExpiredSessions,
  purgeOrphanedUploads,
  registerDataset,
  saveSession,
  touchSession,
} from "./session-store";

let dataRoot: string;

beforeEach(() => {
  dataRoot = path.join(os.tmpdir(), `volt-trace-test-${randomUUID()}`);
  process.env.VOLT_TRACE_DATA_DIR = dataRoot;
});

afterEach(async () => {
  delete process.env.VOLT_TRACE_DATA_DIR;
  await rm(dataRoot, { recursive: true, force: true });
});

describe("session-store", () => {
  it("register and assert dataset ownership", async () => {
    const sessionId = randomUUID();
    const datasetId = randomUUID();
    await touchSession(sessionId);
    await registerDataset(sessionId, datasetId);
    assert.equal(await isDatasetOwned(sessionId, datasetId), true);
    await assertDatasetOwned(sessionId, datasetId);
    await assert.rejects(
      () => assertDatasetOwned(sessionId, randomUUID()),
      DatasetAccessError,
    );
  });

  it("deleteDataset removes dataset directory", async () => {
    const datasetId = randomUUID();
    const dir = datasetPath(datasetId);
    await mkdir(path.join(dir, "sdat"), { recursive: true });
    await writeFile(path.join(dir, ".processed-v1.cache"), "x");
    await deleteDataset(datasetId);
    assert.equal(existsSync(dir), false);
  });

  it("purgeExpiredSessions removes idle sessions and data", async () => {
    const sessionId = randomUUID();
    const datasetId = randomUUID();
    await mkdir(datasetPath(datasetId), { recursive: true });
    await saveSession(sessionId, {
      datasetIds: [datasetId],
      lastSeen: new Date(0).toISOString(),
      expiresAt: new Date(0).toISOString(),
    });
    const removed = await purgeExpiredSessions();
    assert.equal(removed, 1);
    assert.equal(await isDatasetOwned(sessionId, datasetId), false);
  });

  it("destroySession deletes all datasets for session", async () => {
    const sessionId = randomUUID();
    const datasetId = randomUUID();
    await mkdir(datasetPath(datasetId), { recursive: true });
    await touchSession(sessionId);
    await registerDataset(sessionId, datasetId);
    await destroySession(sessionId);
    assert.equal(await isDatasetOwned(sessionId, datasetId), false);
    assert.equal(existsSync(datasetPath(datasetId)), false);
  });

  it("denies expired datasets before the cleanup timer runs", async () => {
    const sessionId = randomUUID();
    const datasetId = randomUUID();
    await mkdir(datasetPath(datasetId), { recursive: true });
    await saveSession(sessionId, {
      datasetIds: [datasetId],
      lastSeen: new Date(0).toISOString(),
      expiresAt: new Date(0).toISOString(),
    });
    await assert.rejects(() => assertDatasetOwned(sessionId, datasetId), DatasetAccessError);
    await touchSession(sessionId);
    assert.equal(existsSync(datasetPath(datasetId)), false);
    assert.equal(await isDatasetOwned(sessionId, datasetId), false);
  });

  it("ending one session keeps another session's data", async () => {
    const first = randomUUID();
    const second = randomUUID();
    const firstDataset = randomUUID();
    const secondDataset = randomUUID();
    await mkdir(datasetPath(firstDataset), { recursive: true });
    await mkdir(datasetPath(secondDataset), { recursive: true });
    await touchSession(first);
    await touchSession(second);
    await registerDataset(first, firstDataset);
    await registerDataset(second, secondDataset);
    await destroySession(first);
    assert.equal(existsSync(datasetPath(firstDataset)), false);
    assert.equal(await isDatasetOwned(second, secondDataset), true);
    assert.equal(existsSync(datasetPath(secondDataset)), true);
    await assert.rejects(() => registerDataset(first, randomUUID()));
  });

  it("removes abandoned uploads without touching owned datasets", async () => {
    const sessionId = randomUUID();
    const ownedId = randomUUID();
    const orphanId = randomUUID();
    const orphanRaw = `${datasetPath(orphanId)}_raw`;
    await mkdir(datasetPath(ownedId), { recursive: true });
    await mkdir(orphanRaw, { recursive: true });
    await touchSession(sessionId);
    await registerDataset(sessionId, ownedId);
    const old = new Date(0);
    await utimes(datasetPath(ownedId), old, old);
    await utimes(orphanRaw, old, old);
    await purgeOrphanedUploads();
    assert.equal(existsSync(datasetPath(ownedId)), true);
    assert.equal(existsSync(orphanRaw), false);
  });
});
