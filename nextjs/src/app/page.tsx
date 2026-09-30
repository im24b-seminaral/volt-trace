import FileUpload from "@/components/FileUpload";
import ConsumptionChart from "@/components/ConsumptionChart";
import MeterReadingChart from "@/components/MeterReadingChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { datasetPath, runPython } from "@/lib/python";
import type { Sensor, SensorSeries, DataPoint } from "@/lib/types";

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const query = await searchParams;
  const get = (key: string) => typeof query[key] === "string" ? query[key] as string : "";
  const dataset = get("dataset");
  const kind = get("kind") === "meter-reading" ? "meter-reading" : "consumption";
  const resolution = get("resolution") === "15min" ? "15min" : "day";
  const from = get("from");
  const to = get("to");
  let sensors: Sensor[] = [];
  let sensorId = get("sensor");
  let points: DataPoint[] = [];
  let error = "";
  if (dataset) {
    try {
      const directory = datasetPath(dataset);
      sensors = JSON.parse(await runPython("sensors", directory));
      if (!sensors.some((sensor) => sensor.sensorId === sensorId)) sensorId = sensors[0]?.sensorId ?? "";
      if (from && to && from > to) throw new Error("Ungültiger Zeitraum.");
      if (sensorId) {
        const series: SensorSeries[] = JSON.parse(await runPython("series", directory, sensorId, kind, resolution,
          from ? `${from}T00:00:00Z` : "", to ? `${to}T23:59:59.999999Z` : ""));
        points = series[0]?.data ?? [];
      }
    } catch (cause) {
      console.error(cause);
      error = "Daten konnten nicht geladen werden. Bitte Datensatz und Zeitraum prüfen.";
    }
  }
  const sensor = sensors.find((item) => item.sensorId === sensorId);
  return <main className="mx-auto max-w-5xl space-y-5 p-5 sm:p-8">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-2xl font-semibold">Messdaten</h1>
      <FileUpload />
    </div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {Number(get("skipped")) > 0 && <p className="text-sm">{Number(get("skipped"))} Datei(en) übersprungen.</p>}
    <form action="/" className="space-y-3">
      <input type="hidden" name="dataset" value={dataset} />
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <div className="space-y-1.5"><Label htmlFor="sensor">Sensor</Label>
          <NativeSelect id="sensor" name="sensor" className="w-full" defaultValue={sensorId} disabled={!sensors.length}>
            {sensors.length ? sensors.map((item) => <NativeSelectOption key={item.sensorId} value={item.sensorId}>{item.sensorId}</NativeSelectOption>) : <NativeSelectOption value="">–</NativeSelectOption>}
          </NativeSelect>
        </div>
        <div className="space-y-1.5"><Label htmlFor="from">Von (UTC)</Label><Input id="from" name="from" type="date" defaultValue={from} disabled={!dataset} /></div>
        <div className="space-y-1.5"><Label htmlFor="to">Bis (UTC)</Label><Input id="to" name="to" type="date" defaultValue={to} disabled={!dataset} /></div>
        <div className="space-y-1.5"><Label htmlFor="resolution">Auflösung</Label><NativeSelect id="resolution" name="resolution" className="w-full" defaultValue={resolution} disabled={!dataset}>
          <NativeSelectOption value="day">Tag</NativeSelectOption><NativeSelectOption value="15min">15 Minuten</NativeSelectOption>
        </NativeSelect></div>
        <div className="space-y-1.5"><Label htmlFor="kind">Diagramm</Label><NativeSelect id="kind" name="kind" className="w-full" defaultValue={kind} disabled={!dataset}>
          <NativeSelectOption value="consumption">Verbrauch</NativeSelectOption><NativeSelectOption value="meter-reading">Zählerstand</NativeSelectOption>
        </NativeSelect></div>
      </div>
      <div className="flex gap-2"><Button disabled={!dataset}>Anzeigen</Button>
        {sensor?.hasMeterReadings && <Button variant="outline" asChild><a href={`/download/${dataset}/${encodeURIComponent(sensorId)}`}>CSV exportieren</a></Button>}
      </div>
    </form>
    <Card><CardContent className="pt-6">
      {!dataset ? <p className="py-24 text-center text-muted-foreground">XML-Dateien oder Ordner wählen.</p>
        : error ? null
        : kind === "consumption" ? <ConsumptionChart data={points} /> : <MeterReadingChart data={points} />}
    </CardContent></Card>
  </main>;
}
