"use client";

import { useEffect, useState } from "react";
import FileUpload from "@/components/FileUpload";
import ConsumptionChart from "@/components/ConsumptionChart";
import MeterReadingChart from "@/components/MeterReadingChart";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getExportCsvUrl, getSensors, getSeries, uploadDataset, type DataPoint, type MeasurementKind, type Resolution, type Sensor } from "@/lib/python";

export default function Home() {
  const [datasetId, setDatasetId] = useState("");
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [sensorId, setSensorId] = useState("");
  const [kind, setKind] = useState<MeasurementKind>("consumption");
  const [resolution, setResolution] = useState<Resolution>("day");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [points, setPoints] = useState<DataPoint[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const sensor = sensors.find((item) => item.sensorId === sensorId);

  async function handleUpload(files: File[]) {
    setBusy(true);
    setError("");
    setDatasetId("");
    setPoints([]);
    try {
      const result = await uploadDataset(files);
      const available = await getSensors(result.datasetId);
      setSensors(available);
      setSensorId(available[0]?.sensorId ?? "");
      setDatasetId(result.datasetId);
      if (result.skippedFiles) setError(`${result.skippedFiles} Datei(en) wurden übersprungen.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Upload fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!datasetId || !sensorId) return;
    let active = true;
    setLoading(true);
    setError("");
    getSeries({ datasetId, sensorId, kind, resolution, from, to })
      .then((series) => { if (active) setPoints(series[0]?.data ?? []); })
      .catch((cause) => { if (active) { setPoints([]); setError(cause instanceof Error ? cause.message : "Daten konnten nicht geladen werden."); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [datasetId, sensorId, kind, resolution, from, to]);

  return (
    <main className="mx-auto max-w-5xl space-y-5 p-5 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Messdaten</h1>
        <div className="flex gap-2">
          <FileUpload busy={busy} onFilesSelected={handleUpload} />
          {datasetId && sensor?.hasMeterReadings && <Button variant="outline" asChild>
            <a href={getExportCsvUrl(datasetId, sensorId)} download={`${sensorId}.csv`}>CSV exportieren</a>
          </Button>}
        </div>
      </div>

      {error && <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="grid gap-3 sm:grid-cols-4">
        <div className="space-y-1.5"><Label htmlFor="sensor">Sensor</Label><NativeSelect className="w-full" id="sensor" value={sensorId} disabled={!sensors.length} onChange={(event) => setSensorId(event.target.value)}>
          {sensors.length ? sensors.map((item) => <NativeSelectOption key={item.sensorId} value={item.sensorId}>{item.label} ({item.sensorId})</NativeSelectOption>) : <NativeSelectOption value="">–</NativeSelectOption>}
        </NativeSelect></div>
        <div className="space-y-1.5"><Label htmlFor="from">Von</Label><Input id="from" type="date" value={from} onChange={(event) => setFrom(event.target.value)} disabled={!datasetId} /></div>
        <div className="space-y-1.5"><Label htmlFor="to">Bis</Label><Input id="to" type="date" value={to} onChange={(event) => setTo(event.target.value)} disabled={!datasetId} /></div>
        <div className="space-y-1.5"><Label htmlFor="resolution">Auflösung</Label><NativeSelect className="w-full" id="resolution" value={resolution} disabled={!datasetId} onChange={(event) => setResolution(event.target.value as Resolution)}>
          <NativeSelectOption value="day">Tag</NativeSelectOption><NativeSelectOption value="15min" disabled={!from || !to}>15 Minuten (mit Zeitraum)</NativeSelectOption>
        </NativeSelect></div>
      </div>

      <Tabs value={kind} onValueChange={(value) => setKind(value as MeasurementKind)}>
        <TabsList><TabsTrigger value="consumption">Verbrauch</TabsTrigger><TabsTrigger value="meter-reading">Zählerstand</TabsTrigger></TabsList>
      </Tabs>
      <Card><CardContent className="pt-6">
        {!datasetId ? <p className="py-24 text-center text-muted-foreground">XML-Dateien wählen, um Messdaten anzuzeigen.</p>
          : loading ? <p className="py-24 text-center text-muted-foreground" role="status">Lade Daten …</p>
          : kind === "meter-reading" && !sensor?.hasMeterReadings ? <p className="py-24 text-center text-muted-foreground">Für diesen Sensor gibt es keinen Zählerstand.</p>
          : kind === "consumption" ? <ConsumptionChart data={points} /> : <MeterReadingChart data={points} />}
      </CardContent></Card>
    </main>
  );
}
