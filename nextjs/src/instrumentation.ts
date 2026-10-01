export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;

  const { purgeExpiredSessions, purgeOrphanedUploads } = await import("./lib/session-store");
  const cleanup = async () => {
    await purgeExpiredSessions();
    await purgeOrphanedUploads();
  };
  await cleanup();
  const timer = setInterval(() => {
    void cleanup().catch(console.error);
  }, 30_000);
  timer.unref();
}
