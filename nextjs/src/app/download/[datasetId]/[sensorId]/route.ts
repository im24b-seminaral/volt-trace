import { datasetPath, runPython } from "@/lib/python";

export async function GET(_request: Request, { params }: { params: Promise<{ datasetId: string; sensorId: string }> }) {
  const { datasetId, sensorId } = await params;
  if (!/^[a-zA-Z0-9_-]+$/.test(sensorId)) return new Response("Ungültiger Sensor", { status: 400 });
  try {
    const csv = await runPython("export", datasetPath(datasetId), sensorId);
    return new Response(csv, { headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": `attachment; filename="${sensorId}.csv"`,
    } });
  } catch (error) {
    console.error(error);
    return new Response("Export fehlgeschlagen", { status: 500 });
  }
}
