import Link from "next/link";
import { notFound } from "next/navigation";

import ImportIssues from "@/components/ImportIssues";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  DIRECTION_LABELS, FILE_TYPE_LABELS, formatCount, formatPeriod, readImportReport,
} from "@/lib/import-report";
import { DatasetAccessError, getOrCreateSession, resolveOwnedDatasetPath } from "@/lib/session";
import type { ImportReport } from "@/lib/types";

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return <Card size="sm">
    <CardContent className="space-y-0.5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{hint}</p>
    </CardContent>
  </Card>;
}

/** "5'133 sdat · 47 ESL" – die Aufteilung der gefundenen Dateien als Nebensatz. */
function typeBreakdown(report: ImportReport): string {
  const parts = report.files
    .filter((row) => row.found > 0)
    .map((row) => `${formatCount(row.found)} ${FILE_TYPE_LABELS[row.type]}`);
  return parts.join(" · ") || "keine Dateien";
}

export default async function ImportReportPage({ params }: { params: Promise<{ dataset: string }> }) {
  const { dataset } = await params;
  let directory: string;
  try {
    directory = await resolveOwnedDatasetPath(await getOrCreateSession(), dataset);
  } catch (cause) {
    if (!(cause instanceof DatasetAccessError)) throw cause;
    return <main className="mx-auto max-w-3xl p-5 py-16 sm:p-8">
      <Alert variant="destructive">
        <AlertTitle>Datensatz nicht verfügbar</AlertTitle>
        <AlertDescription>
          Dieser Datensatz gehört nicht zu Ihrer Sitzung.
          <Button variant="outline" asChild className="mt-3 w-fit"><Link href="/">Zur Startseite</Link></Button>
        </AlertDescription>
      </Alert>
    </main>;
  }

  const report = await readImportReport(directory);
  if (!report) notFound();

  const chart = `/?dataset=${encodeURIComponent(dataset)}`;
  const toChart = <Button asChild><Link href={chart}>Weiter zur Auswertung</Link></Button>;

  return <main className="mx-auto max-w-5xl space-y-8 p-5 py-10 sm:p-8">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Importbericht</h1>
        <p className="text-muted-foreground">Was aus den hochgeladenen Dateien gelesen wurde.</p>
      </div>
      {toChart}
    </div>

    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Stat label="Dateien gefunden" value={formatCount(report.foundFiles)} hint={typeBreakdown(report)} />
      <Stat label="Eingelesen" value={formatCount(report.processedFiles)} hint="inkl. Unterordner" />
      <Stat label="Übersprungen" value={formatCount(report.skippedFiles)}
        hint={report.skippedFiles ? "mit Begründung, siehe Hinweise" : "keine Datei verworfen"} />
      <Stat label="Messpunkte" value={formatCount(report.measurementPoints)}
        hint="nach Auflösung der Duplikate" />
    </div>

    <section className="space-y-3" aria-labelledby="dateien">
      <h2 id="dateien" className="font-heading font-medium">Dateien</h2>
      <Card size="sm">
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Typ</TableHead>
                <TableHead className="text-right">Gefunden</TableHead>
                <TableHead className="text-right">Eingelesen</TableHead>
                <TableHead className="text-right">Übersprungen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.files.map((row) => <TableRow key={row.type}>
                <TableCell>{FILE_TYPE_LABELS[row.type]}</TableCell>
                <TableCell className="text-right tabular-nums">{formatCount(row.found)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatCount(row.processed)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatCount(row.skipped)}</TableCell>
              </TableRow>)}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell>Total</TableCell>
                <TableCell className="text-right tabular-nums">{formatCount(report.foundFiles)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatCount(report.processedFiles)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatCount(report.skippedFiles)}</TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </CardContent>
      </Card>
    </section>

    {report.findings.length > 0 && <section className="space-y-3" aria-labelledby="hinweise">
      <h2 id="hinweise" className="font-heading font-medium">Hinweise</h2>
      <ul className="space-y-2">
        {report.findings.map((finding) => <li key={`${finding.label}${finding.text}`}
          className="rounded-lg bg-muted/50 px-3 py-2 text-sm">
          <span className="font-medium">{finding.label}</span> {finding.text}
        </li>)}
      </ul>
    </section>}

    <section className="space-y-3" aria-labelledby="sensoren">
      <h2 id="sensoren" className="font-heading font-medium">Sensoren</h2>
      <Card size="sm">
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Sensor</TableHead>
                <TableHead>Richtung</TableHead>
                <TableHead className="text-right">Messwerte</TableHead>
                <TableHead>Zeitraum</TableHead>
                <TableHead>Zählerstände</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.sensors.map((sensor) => <TableRow key={sensor.sensorId}>
                <TableCell className="font-medium">{sensor.sensorId}</TableCell>
                <TableCell>{DIRECTION_LABELS[sensor.direction]}</TableCell>
                <TableCell className="text-right tabular-nums">{formatCount(sensor.values)}</TableCell>
                <TableCell className="whitespace-nowrap tabular-nums">{formatPeriod(sensor)}</TableCell>
                <TableCell className="text-muted-foreground">
                  {sensor.eslReadings
                    ? `ESL · ${formatCount(sensor.eslReadings)} ${sensor.eslReadings === 1 ? "Ablesung" : "Ablesungen"}`
                    : "ohne ESL"}
                </TableCell>
              </TableRow>)}
              {report.sensors.length === 0 && <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground">Keine Sensoren gefunden.</TableCell>
              </TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </section>

    <ImportIssues issues={report.issues} />

    <div className="flex justify-end border-t pt-5">{toChart}</div>
  </main>;
}
