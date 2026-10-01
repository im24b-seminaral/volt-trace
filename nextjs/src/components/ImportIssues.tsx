import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ImportIssue } from "@/lib/types";

/** Jede übersprungene Datei und jeder übersprungene Datensatz mit Grund (NFA-06). */
export default function ImportIssues({ issues }: { issues: ImportIssue[] }) {
  if (!issues.length) return null;

  return <Collapsible>
    <CollapsibleTrigger asChild><Button variant="ghost">Meldungen und Gründe ({issues.length})</Button></CollapsibleTrigger>
    <CollapsibleContent>
      <ScrollArea className="mt-2 h-64 rounded-md border border-border/50">
        <ul className="space-y-2 p-3 text-sm">
          {issues.map((issue, index) => <li key={index} className="break-words">
            {issue.file}{issue.meter ? ` · Meter ${issue.meter}` : ""}{issue.obis ? ` · OBIS ${issue.obis}` : ""}: {issue.reason}
            {issue.skippedRecords > 0 ? ` (${issue.skippedRecords} Datensatz)` : ""}
          </li>)}
        </ul>
      </ScrollArea>
    </CollapsibleContent>
  </Collapsible>;
}
