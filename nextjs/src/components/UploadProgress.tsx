"use client";

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { PYTHON_TIMEOUT_MS } from "@/lib/constants";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const STEPS = [
  { id: "transfer", label: "Übertragung an die Datenverarbeitung" },
  { id: "write", label: "Dateien entgegennehmen" },
  { id: "sort", label: "Dateien sortieren" },
  { id: "sdat", label: "sdat-Dateien einlesen" },
  { id: "esl", label: "ESL-Dateien einlesen" },
  { id: "prepare", label: "Diagramm vorbereiten" },
] as const;

export type StepId = (typeof STEPS)[number]["id"];
export type UploadState = {
  startedAt: number;
  index: number;
  values: Partial<Record<StepId, { done: number; total: number }>>;
};

export const stepIndex = (step: StepId) => STEPS.findIndex((entry) => entry.id === step);

const number = new Intl.NumberFormat("de-CH");
const megabytes = new Intl.NumberFormat("de-CH", { maximumFractionDigits: 1 });

function detail(step: StepId, value: { done: number; total: number } | undefined): string {
  if (!value?.total) return "";   // Schritte ohne Zählung bleiben ohne Zahl
  if (step === "transfer") return `${megabytes.format(value.done / 1048576)} / ${megabytes.format(value.total / 1048576)} MB`;
  if (value.done < value.total) return `${number.format(value.done)} / ${number.format(value.total)} Dateien`;
  return `${number.format(value.total)} Dateien`;
}

export default function UploadProgress({ state }: { state: UploadState }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, []);

  const current = state.values[STEPS[state.index].id];
  const fraction = current?.total ? Math.min(1, current.done / current.total) : 0;
  const percent = Math.min(99, Math.round(((state.index + fraction) / STEPS.length) * 100));
  const elapsed = Math.max(0, Math.floor((now - state.startedAt) / 1000));

  return <Card>
    <CardContent className="space-y-4 pt-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-medium">Daten werden eingelesen</h2>
        <p className="text-sm text-muted-foreground tabular-nums">
          {percent} % · Verstrichen {elapsed} s · Zeitbudget {PYTHON_TIMEOUT_MS / 1000} s
        </p>
      </div>
      <div role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}
        aria-label="Fortschritt des Imports" className="h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${percent}%` }} />
      </div>
      <ol className="space-y-1">
        {STEPS.map((step, index) => <li key={step.id} aria-current={index === state.index || undefined}
          className={cn("flex flex-wrap items-center justify-between gap-x-3 gap-y-0.5 rounded-md px-2 py-1 text-sm",
            index > state.index && "text-muted-foreground/60",
            index === state.index && "bg-accent font-medium")}>
          <span className="flex items-center gap-2">
            <span aria-hidden className="flex size-4 shrink-0 items-center justify-center">
              {index < state.index ? <Check className="size-4" />
                : index === state.index ? <Loader2 className="size-4 animate-spin" />
                : <span className="size-1.5 rounded-full bg-current" />}
            </span>
            {step.label}
          </span>
          <span className="tabular-nums text-muted-foreground">{detail(step.id, state.values[step.id])}</span>
        </li>)}
      </ol>
    </CardContent>
  </Card>;
}
