import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
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
  registerDataset,
  saveSession,
  touchSession,
} from "./session-store";

let dataRoot: string;

beforeEach(() => {
  dataRoot = path.join(os.tmpdir(), `volt-trace-test-${randomUUID()}`);
  process.env.VOLT_TRACE_DATA_DIR = dataRoot;
});

afterEach(() => {
  delete process.env.VOLT_TRACE_DATA_DIR;
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
  });
});
