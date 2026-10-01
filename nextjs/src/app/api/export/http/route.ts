import { runPython } from "@/lib/python";
import { DatasetAccessError, getSessionIdFromCookies, resolveOwnedDatasetPath } from "@/lib/session";

export async function POST(request: Request) {
  let input: Record<string, unknown>;
  try {
    input = await request.json();
    if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("invalid body");
  } catch {
    return Response.json({ message: "Ungültige Anfrage." }, { status: 400 });
  }

  const { datasetId, sensorId, kind, url } = input;
  if (typeof datasetId !== "string" || typeof sensorId !== "string" ||
      !/^[a-zA-Z0-9_-]+$/.test(sensorId) ||
      (kind !== "verbrauch" && kind !== "zaehlerstand") || typeof url !== "string") {
    return Response.json({ message: "Ungültige Exportdaten." }, { status: 400 });
  }

  let target: URL;
  try {
    target = new URL(url);
    if (!["http:", "https:"].includes(target.protocol) || target.username || target.password) {
      throw new Error("invalid URL");
    }
  } catch {
    return Response.json({ message: "Bitte eine gültige HTTP- oder HTTPS-URL eingeben." }, { status: 400 });
  }

  try {
    const sessionId = await getSessionIdFromCookies();
    if (!sessionId) throw new DatasetAccessError();
    const directory = await resolveOwnedDatasetPath(sessionId, datasetId);
    const json = await runPython("export", directory, sensorId, kind, "json");
    const upstream = await fetch(target, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: json,
      redirect: "error",
      signal: AbortSignal.timeout(30_000),
    });
    const body = (await upstream.text()).slice(0, 5_000);
    let message = body;
    try {
      const parsed: unknown = JSON.parse(body);
      if (parsed && typeof parsed === "object" && "message" in parsed &&
          typeof parsed.message === "string") message = parsed.message;
    } catch {
      // Textantworten werden unverändert angezeigt.
    }
    return Response.json({
      ok: upstream.ok,
      message: upstream.ok ? (message || `HTTP ${upstream.status} ${upstream.statusText}`.trim())
        : `HTTP ${upstream.status}: ${message || upstream.statusText}`,
    });
  } catch (error) {
    if (error instanceof DatasetAccessError) {
      return Response.json({ message: "Datensatz nicht verfügbar." }, { status: 403 });
    }
    if ((error as { code?: unknown }).code === 1) {
      return Response.json({ message: "Keine Daten für diesen Export vorhanden." }, { status: 404 });
    }
    console.error(error);
    return Response.json({ message: "HTTP-POST fehlgeschlagen. Zieladresse und Server prüfen." }, { status: 502 });
  }
}
