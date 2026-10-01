import Link from "next/link";
import ImportIssues from "@/components/ImportIssues";
import { Button } from "@/components/ui/button";
import { formatCount, readImportReport } from "@/lib/import-report";

export default async function ImportReport({ dataset, directory }: { dataset: string; directory: string }) {
  const report = await readImportReport(directory);
  if (!report) return null;

  return <section className="space-y-2 rounded-lg border p-4" aria-label="Importbericht">
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="font-semibold">Importbericht</h2>
      <Button variant="link" asChild className="h-auto p-0">
        <Link href={`/import/${encodeURIComponent(dataset)}`}>Vollständigen Bericht ansehen</Link>
      </Button>
    </div>
    <p className="text-sm">Gefunden: {formatCount(report.foundFiles)} Dateien · Eingelesen: {formatCount(report.processedFiles)} · Übersprungen: {formatCount(report.skippedFiles)} Dateien und {formatCount(report.skippedRecords)} Datensätze</p>
    {report.findings.map((finding) => <p key={`${finding.label}${finding.text}`} className="text-sm">
      <span className="font-medium">{finding.label}</span> {finding.text}
    </p>)}
    <ImportIssues issues={report.issues} />
  </section>;
}
