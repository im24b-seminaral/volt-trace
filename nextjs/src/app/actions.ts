"use server";

import { endSession } from "@/lib/session";

export async function clearSession(): Promise<void> {
  await endSession();
}
