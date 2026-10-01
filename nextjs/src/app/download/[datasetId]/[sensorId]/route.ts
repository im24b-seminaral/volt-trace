import { runPython } from "@/lib/python";
import { DatasetAccessError, getOrCreateSession, resolveOwnedDatasetPath } from "@/lib/session";

const KINDS = ["verbrauch", "zaehlerstand"];   // FA-10a / FA-10b
const FORMATS = ["csv", "json"];               // FA-10 / FA-13

export async function GET(request: Request, { params }: { params: Promise<{ datasetId: string; sensorId: string }> }) {
  const { datasetId, sensorId } = await params;
  const searchParams = new URL(request.url).searchParams;
  const kind = searchParams.get("kind") ?? "";
  const format = searchParams.get("format") ?? "csv";   // FA-13: json
  if (!/^[a-zA-Z0-9_-]+$/.test(sensorId)) return new Response("Ungültiger Sensor", { status: 400 });
  if (!KINDS.includes(kind) || !FORMATS.includes(format)) return new Response("Ungültige Exportart", { status: 400 });
  try {
    const sessionId = await getOrCreateSession();
    const directory = await resolveOwnedDatasetPath(sessionId, datasetId);
    const body = await runPython("export", directory, sensorId, kind, format);
    return new Response(body, { headers: {
      "Content-Type": format === "json" ? "application/json; charset=utf-8" : "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${sensorId}_${kind}.${format}"`,
    } });
  } catch (error) {
    console.error(error);
    if (error instanceof DatasetAccessError) {
      return new Response("Datensatz nicht verfügbar", { status: 403 });
    }
    // Exit-Code 1: für diesen Sensor gibt es keine Daten dieser Art.
    if ((error as { code?: unknown }).code === 1) {
      return new Response("Keine Daten für diesen Export vorhanden", { status: 404 });
    }
    return new Response("Export fehlgeschlagen", { status: 500 });
  }
}
