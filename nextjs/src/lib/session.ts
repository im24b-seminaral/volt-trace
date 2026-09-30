import "server-only";
import { randomUUID } from "node:crypto";

import { cookies } from "next/headers";

import { SESSION_COOKIE_NAME } from "@/lib/constants";
import {
  assertDatasetOwned,
  destroySession,
  maybePurgeExpiredThrottled,
  registerDataset,
  resolveOwnedDatasetPath,
  touchSession,
} from "@/lib/session-store";

const UUID_RE = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;

export {
  DatasetAccessError,
  deleteDataset,
  destroySession,
  purgeExpiredSessions,
  registerDataset,
  assertDatasetOwned,
  resolveOwnedDatasetPath,
} from "@/lib/session-store";

export async function getOrCreateSession(): Promise<string> {
  await maybePurgeExpiredThrottled();
  const cookieStore = await cookies();
  let sessionId = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!sessionId || !UUID_RE.test(sessionId)) {
    sessionId = randomUUID();
    cookieStore.set(SESSION_COOKIE_NAME, sessionId, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
    });
  }
  await touchSession(sessionId);
  return sessionId;
}

export async function getSessionIdFromCookies(): Promise<string | null> {
  const sessionId = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  return sessionId && UUID_RE.test(sessionId) ? sessionId : null;
}

export async function endSession(): Promise<void> {
  const sessionId = await getSessionIdFromCookies();
  if (sessionId) {
    await destroySession(sessionId);
  }
  (await cookies()).set(SESSION_COOKIE_NAME, "", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
}
