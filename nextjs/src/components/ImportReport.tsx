import { readFile } from "node:fs/promises";
import path from "node:path";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ImportReport as ImportReportData } from "@/lib/types";

export default async function ImportReport({ directory }: { directory: string }) {
  let report: ImportReportData;
  try {
    report = JSON.parse(await readFile(path.join(directory, "import-report.json"), "utf-8")) as ImportReportData;
  } catch { return null; }

  return <section className="space-y-2 rounded-lg border p-4" aria-label="Importbericht">
    <h2 className="font-semibold">Importbericht</h2>
    <p className="text-sm">Gefunden: {report.foundFiles} Dateien · Eingelesen: {report.processedFiles} · Übersprungen: {report.skippedFiles} Dateien und {report.skippedRecords} Datensätze</p>
    {report.findings.map((finding) => <p key={finding} className="text-sm">{finding}</p>)}
    {report.issues.length > 0 && <Collapsible>
      <CollapsibleTrigger asChild><Button variant="ghost">Meldungen und Gründe ({report.issues.length})</Button></CollapsibleTrigger>
      <CollapsibleContent>
        <ScrollArea className="mt-2 h-64 rounded-md border border-border/50">
          <ul className="space-y-2 p-3 text-sm">
            {report.issues.map((issue, index) => <li key={index} className="break-words">
              {issue.file}{issue.meter ? ` · Meter ${issue.meter}` : ""}{issue.obis ? ` · OBIS ${issue.obis}` : ""}: {issue.reason}
              {issue.skippedRecords > 0 ? ` (${issue.skippedRecords} Datensatz)` : ""}
            </li>)}
          </ul>
        </ScrollArea>
      </CollapsibleContent>
    </Collapsible>}
  </section>;
}
