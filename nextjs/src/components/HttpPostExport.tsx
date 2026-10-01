"use client";

import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Kind = "verbrauch" | "zaehlerstand";

export default function HttpPostExport({ dataset, sensorId, hasConsumption, hasMeterReadings }: {
  dataset: string;
  sensorId: string;
  hasConsumption: boolean;
  hasMeterReadings: boolean;
}) {
  const urlId = useId();
  const [isOpen, setIsOpen] = useState(false);
  const [kind, setKind] = useState<Kind>("verbrauch");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  function open(selected: Kind) {
    setKind(selected);
    setResult(null);
    setIsOpen(true);
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const url = String(new FormData(event.currentTarget).get("url") ?? "");
    setSending(true);
    setResult(null);
    try {
      const response = await fetch("/api/export/http", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ datasetId: dataset, sensorId, kind, url }),
      });
      const reply = await response.json() as { ok?: boolean; message?: string };
      setResult({ ok: response.ok && reply.ok === true, message: reply.message ?? "Keine Antwort vom Server." });
    } catch {
      setResult({ ok: false, message: "Verbindung fehlgeschlagen. Bitte erneut versuchen." });
    } finally {
      setSending(false);
    }
  }

  return <Dialog open={isOpen} onOpenChange={(next) => { if (!sending) setIsOpen(next); }}>
    {hasConsumption && <Button type="button" variant="outline" onClick={() => open("verbrauch")}>SDAT (HTTP POST)</Button>}
    {hasMeterReadings && <Button type="button" variant="outline" onClick={() => open("zaehlerstand")}>ESL (HTTP POST)</Button>}
    <DialogContent showCloseButton={!sending}>
      <form onSubmit={send} className="space-y-4">
        <DialogHeader>
          <DialogTitle>{kind === "verbrauch" ? "SDAT-Verbrauch" : "ESL-Zählerstände"} per HTTP POST senden</DialogTitle>
          <DialogDescription>JSON-Daten für Sensor {sensorId} an eine Zieladresse senden.</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor={urlId}>Zieladresse</Label>
          <Input id={urlId} name="url" type="url" required placeholder="https://example.com/measurements" />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" disabled={sending} onClick={() => setIsOpen(false)}>Schliessen</Button>
          <Button type="submit" disabled={sending}>{sending ? "Sende…" : "Senden"}</Button>
        </DialogFooter>
        {result && <p role={result.ok ? "status" : "alert"} className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-md border p-3 text-sm">
          {result.message}
        </p>}
      </form>
    </DialogContent>
  </Dialog>;
}
