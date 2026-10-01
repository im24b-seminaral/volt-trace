"use server";

import { endSession } from "@/lib/session";
import { redirect } from "next/navigation";

export async function clearSession(): Promise<void> {
  await endSession();
  redirect("/");
}
