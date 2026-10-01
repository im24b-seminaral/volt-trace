import { importUpload } from "@/lib/import";

export const dynamic = "force-dynamic";

/**
 * Nimmt den Upload entgegen und schickt den Fortschritt als NDJSON zurück,
 * solange die Verarbeitung läuft. Die letzte Zeile trägt das Ergebnis.
 * Eine Server Action käme dafür nicht in Frage: sie antwortet erst am Ende.
 */
export async function POST(request: Request) {
  const form = await request.formData();
  const encoder = new TextEncoder();
  let live = true;
  const abort = new AbortController();
  request.signal.addEventListener("abort", () => abort.abort(), { once: true });
  if (request.signal.aborted) abort.abort();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (event: unknown) => {
        if (live) controller.enqueue(encoder.encode(`${JSON.stringify(event)}\n`));
      };
      const result = await importUpload(form, send, abort.signal);
      send("datasetId" in result ? { dataset: result.datasetId } : { error: result.error });
      if (live) controller.close();
    },
    cancel() {
      abort.abort();
      live = false;   // Browser ist weg; der Import wird abgebrochen und aufgeräumt.
    },
  });

  return new Response(stream, {
    headers: {
      "content-type": "application/x-ndjson; charset=utf-8",
      "cache-control": "no-store, no-transform",
      "x-accel-buffering": "no",
    },
  });
}
