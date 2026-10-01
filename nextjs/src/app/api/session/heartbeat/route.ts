import { getOrCreateSession } from "@/lib/session";

export async function POST() {
  await getOrCreateSession();
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}
