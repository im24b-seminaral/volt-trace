import FileUpload from "@/components/FileUpload";
import ConsumptionChart from "@/components/ConsumptionChart";
import MeterReadingChart from "@/components/MeterReadingChart";
import ChartForm from "@/components/ChartForm";
import ChartFilters from "@/components/ChartFilters";
import ImportReport from "@/components/ImportReport";
import { Button } from "@/components/ui/button";
import { localDayBoundsToUtcIso, localNextDayStartUtcIso } from "@/lib/datetime";
import { runPython } from "@/lib/python";
import { DatasetAccessError, getOrCreateSession, resolveOwnedDatasetPath } from "@/lib/session";
import type { Sensor, SensorSeries } from "@/lib/types";

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const query = await searchParams;
  const get = (key: string) => typeof query[key] === "string" ? query[key] as string : "";
  const dataset = get("dataset");
  const kind = get("kind") === "meter-reading" ? "meter-reading" : "consumption";
  let resolution: "day" | "15min" = "day";
  const from = get("from");
  const to = get("to");
  let sensors: Sensor[] = [];
  let selected = typeof query.sensor === "string" ? [query.sensor] : query.sensor ?? [];
  let series: SensorSeries[] = [];
  let first = "";
  let last = "";
  let error = "";
  let directory = "";
  if (dataset) {
    try {
      const sessionId = await getOrCreateSession();
      directory = await resolveOwnedDatasetPath(sessionId, dataset);
      sensors = JSON.parse(await runPython("sensors", directory));
      selected = [...new Set(selected)].filter((id) => sensors.some((sensor) => sensor.sensorId === id));
      if (query.sensor === undefined) selected = sensors.slice(0, 1).map((sensor) => sensor.sensorId);
      const dates = sensors.filter((sensor) => selected.includes(sensor.sensorId))
        .flatMap((sensor) => kind === "consumption" ? sensor.consumptionDates : sensor.meterReadingDates).sort();
      first = dates[0] ?? "";
      last = dates.at(-1) ?? "";
      const days = (Date.parse(to || last) - Date.parse(from || first)) / 86400000 + 1;
      resolution = days > 0 && days <= 7 ? "15min" : "day";
      if (from && to && from > to) error = "Das Enddatum muss nach dem Startdatum liegen.";
      if (!selected.length) error = "Bitte mindestens einen Sensor auswählen.";
      if (selected.length && !error) {
        const fromUtc = from ? localDayBoundsToUtcIso(from).from : "";
        const toUtc = to ? (kind === "consumption" ? localNextDayStartUtcIso(to)
          : localDayBoundsToUtcIso(to).to) : "";
        series = (await Promise.all(selected.map(async (sensorId): Promise<SensorSeries[]> =>
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
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-2xl font-semibold">Messdaten</h1>
      <FileUpload />
    </div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {directory && <ImportReport directory={directory} />}
    <ChartForm chart={
      error ? null
        : kind === "consumption"
          ? <ConsumptionChart data={series} resolution={resolution} />
          : <MeterReadingChart data={series} resolution={resolution} />
    }>
      <ChartFilters key={[dataset, kind, from, to, ...selected].join("|")}
        dataset={dataset} sensors={sensors} selected={selected} kind={kind}
        from={from} to={to} first={first} last={last} />
    </ChartForm>
    <div className="flex flex-wrap gap-2">
      {sensors.filter((sensor) => selected.includes(sensor.sensorId)).map((sensor) => <div key={sensor.sensorId} className="flex flex-wrap items-center gap-2">
        <span className="text-sm">{sensor.label}</span>
        {sensor.hasConsumption && <Button variant="outline" asChild><a href={`/download/${dataset}/${encodeURIComponent(sensor.sensorId)}?kind=verbrauch`}>Verbrauch (CSV)</a></Button>}
        {sensor.hasMeterReadings && <Button variant="outline" asChild><a href={`/download/${dataset}/${encodeURIComponent(sensor.sensorId)}?kind=zaehlerstand`}>Zählerstände (CSV)</a></Button>}
      </div>)}
    </div>
  </main>;
}
