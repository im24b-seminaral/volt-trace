"use client";

import { Bar, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import type { DataPoint } from "@/lib/types";

export default function EnergyChart({ data, kind }: { data: DataPoint[]; kind: "bar" | "line" }) {
  if (!data.length) return <p className="py-16 text-center text-muted-foreground">Keine Werte im Zeitraum.</p>;
  const label = kind === "bar" ? "Verbrauch (kWh)" : "Zählerstand (kWh)";

  return <div className="space-y-2">
    <p className="text-sm text-muted-foreground">{label} · UTC</p>
    <ChartContainer config={{ value: { label, color: "var(--chart-2)" } }} className="h-80 w-full">
      <ComposedChart accessibilityLayer data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="ts" tickFormatter={(ts: string) => ts.slice(5, 16).replace("T", " ")} minTickGap={32} tickLine={false} />
        <YAxis width={72} tickLine={false} />
        <ChartTooltip content={<ChartTooltipContent labelFormatter={(ts) => String(ts).slice(0, 16).replace("T", " ")} />} />
        {kind === "bar"
          ? <Bar dataKey="value" fill="var(--color-value)" radius={2} isAnimationActive={false} />
          : <Line dataKey="value" stroke="var(--color-value)" strokeWidth={2} dot={data.length === 1} isAnimationActive={false} />}
      </ComposedChart>
    </ChartContainer>
  </div>;
}
