import { runPython } from "@/lib/python";
import { DatasetAccessError, getOrCreateSession, resolveOwnedDatasetPath } from "@/lib/session";

export async function GET(_request: Request, { params }: { params: Promise<{ datasetId: string; sensorId: string }> }) {
  const { datasetId, sensorId } = await params;
  if (!/^[a-zA-Z0-9_-]+$/.test(sensorId)) return new Response("Ungültiger Sensor", { status: 400 });
  try {
    const sessionId = await getOrCreateSession();
    const directory = await resolveOwnedDatasetPath(sessionId, datasetId);
    const csv = await runPython("export", directory, sensorId);
    return new Response(csv, { headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": `attachment; filename="${sensorId}.csv"`,
    } });
  } catch (error) {
    console.error(error);
    if (error instanceof DatasetAccessError) {
      return new Response("Datensatz nicht verfügbar", { status: 403 });
    }
    return new Response("Export fehlgeschlagen", { status: 500 });
  }
}
