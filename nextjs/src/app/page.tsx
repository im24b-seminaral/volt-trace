import FileUpload from "@/components/FileUpload";
import ConsumptionChart from "@/components/ConsumptionChart";
import MeterReadingChart from "@/components/MeterReadingChart";
import ChartForm from "@/components/ChartForm";
import ChartFilters from "@/components/ChartFilters";
import HttpPostExport from "@/components/HttpPostExport";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { localDayBoundsToUtcIso, localNextDayStartUtcIso } from "@/lib/datetime";
import {
  dateRangeError, hasDataFor, importedSensors, parseResolution,
  rangeResolution, sensorDateRange, sensorsFor
} from "@/lib/chart-filters"; import { runPython } from "@/lib/python";
import { DatasetAccessError, getOrCreateSession, resolveOwnedDatasetPath } from "@/lib/session";
import type { Sensor, SensorSeries } from "@/lib/types";

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const query = await searchParams;
  const get = (key: string) => typeof query[key] === "string" ? query[key] as string : "";
  const dataset = get("dataset");
  let kind = get("kind") === "meter-reading" ? "meter-reading" : "consumption";
  let drawable: string[] = [];
  let notice = "";
  let consumptionResolution: "day" | "15min" = "day";
  let resolution: "day" | "15min" = "day";
  let from = get("from");
  let to = get("to");
  let sensors: Sensor[] = [];
  let selected = typeof query.sensor === "string" ? [query.sensor] : query.sensor ?? [];
  let series: SensorSeries[] = [];
  let error = "";
  let directory = "";
  if (dataset) {
    try {
      const sessionId = await getOrCreateSession();
      directory = await resolveOwnedDatasetPath(sessionId, dataset);
      sensors = importedSensors(JSON.parse(await runPython("sensors", directory)));

      // Nur-ESL-Upload: dann ist Zählerstand die sinnvolle Startansicht.
      if (!get("kind") && !sensorsFor(sensors, "consumption").length) kind = "meter-reading";

      const withData = sensorsFor(sensors, kind);
      selected = [...new Set(selected)].filter((id) => sensors.some((s) => s.sensorId === id));
      if (query.sensor === undefined) selected = withData.slice(0, 1).map((s) => s.sensorId);

      const { first, last } = sensorDateRange(withData, kind);
      from = from || first;
      to = to || last;
      consumptionResolution = parseResolution(get("resolution"), from, to);
      resolution = kind === "consumption" ? consumptionResolution : rangeResolution(from, to);

      drawable = selected.filter((id) => withData.some((s) => s.sensorId === id));
      const missing = selected.filter((id) => !drawable.includes(id));

      error = !sensors.length ? "Keine Sensoren mit auswertbaren Daten vorhanden."
        : !selected.length ? "Bitte mindestens einen Sensor auswählen."
          : drawable.length ? dateRangeError(from, to, first, last) : "";

      // FA-09: fehlende Daten benennen, statt Werte zu erfinden.
      notice = missing.length
        ? kind === "consumption"
          ? `Keine Verbrauchsdaten für ${missing.join(", ")}. Verbrauch braucht SDAT-Dateien.`
          : `Keine Zählerstände für ${missing.join(", ")}. Zählerstände brauchen ESL-Dateien.`
        : "";
      if (drawable.length && !error) {
        const fromUtc = from ? localDayBoundsToUtcIso(from).from : "";
        const toUtc = to ? (kind === "consumption" ? localNextDayStartUtcIso(to)
          : localDayBoundsToUtcIso(to).to) : "";
        series = (await Promise.all(drawable.map(async (sensorId): Promise<SensorSeries[]> =>
          JSON.parse(await runPython("series", directory, sensorId, kind, resolution, fromUtc, toUtc))
        ))).flat();
      }
    } catch (cause) {
      console.error(cause);
      error = cause instanceof DatasetAccessError
        ? "Dieser Datensatz gehört nicht zu Ihrer Sitzung."
        : "Daten konnten nicht geladen werden. Bitte Datensatz und Zeitraum prüfen.";
    }
  }
  if (!dataset) return <main className="mx-auto max-w-3xl space-y-8 p-5 py-16 sm:p-8 sm:py-24">
    <div className="space-y-2 text-center">
      <h1 className="text-3xl font-semibold tracking-tight">Messdaten auswerten</h1>
      <p className="text-muted-foreground">SDAT- und ESL-Dateien einlesen, um Verbrauch und Zählerstände zu erkunden und zu exportieren.</p>
    </div>
    <FileUpload variant="start" />
  </main>;
  return <main className="mx-auto max-w-5xl space-y-5 p-5 sm:p-8">
    <div className="flex items-center justify-between gap-3">
      <h1 className="text-2xl font-semibold">Messdaten</h1>
      {directory && <Button variant="outline" asChild>
        <Link href={`/import/${encodeURIComponent(dataset)}`}>Bericht ansehen</Link>
      </Button>}
    </div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {notice && <p role="status" className="text-sm text-muted-foreground">{notice}</p>}
    <ChartForm chart={
      error || !drawable.length ? null
        : kind === "consumption"
          ? <ConsumptionChart data={series} resolution={resolution} />
          : <MeterReadingChart data={series} resolution={resolution} />
    }>
      <ChartFilters key={[dataset, kind, from, to, consumptionResolution, ...selected].join("|")}
        dataset={dataset} sensors={sensors} selected={selected} kind={kind}
        from={from} to={to} resolution={consumptionResolution} />
    </ChartForm>
    <div className="flex flex-col items-start gap-2">
      {sensors.filter((sensor) => selected.includes(sensor.sensorId)).map((sensor) => <div key={sensor.sensorId} className="flex flex-wrap items-center gap-2">
        <span className="text-sm">{sensor.label}</span>
        <Collapsible className="group flex flex-wrap items-center gap-2">
          <CollapsibleTrigger asChild><Button variant="outline">
            Export <ChevronRight className="transition-transform group-data-[state=open]:rotate-90" />
          </Button></CollapsibleTrigger>
          <CollapsibleContent className="flex flex-wrap gap-2">
            {sensor.hasConsumption && ["csv", "json"].map((format) => <Button key={format} variant="outline" asChild><a href={`/download/${dataset}/${encodeURIComponent(sensor.sensorId)}?kind=verbrauch&format=${format}`}>Verbrauch ({format.toUpperCase()})</a></Button>)}
            {sensor.hasMeterReadings && ["csv", "json"].map((format) => <Button key={format} variant="outline" asChild><a href={`/download/${dataset}/${encodeURIComponent(sensor.sensorId)}?kind=zaehlerstand&format=${format}`}>Zählerstände ({format.toUpperCase()})</a></Button>)}
            <HttpPostExport dataset={dataset} sensorId={sensor.sensorId}
              hasConsumption={sensor.hasConsumption} hasMeterReadings={sensor.hasMeterReadings} />
          </CollapsibleContent>
        </Collapsible>
      </div>)}
    </div>
  </main>;
}
