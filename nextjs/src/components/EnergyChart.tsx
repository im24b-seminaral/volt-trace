"use client";

import { Bar, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { formatChartLabel } from "@/lib/datetime";
import type { DataPoint } from "@/lib/types";

export default function EnergyChart({
  data,
  kind,
  resolution,
}: {
  data: DataPoint[];
  kind: "bar" | "line";
  resolution: "day" | "15min";
}) {
  if (!data.length) return <p className="py-16 text-center text-muted-foreground">Keine Werte im Zeitraum.</p>;
  const label = kind === "bar" ? "Verbrauch (kWh)" : "Zählerstand (kWh)";

  return <div className="space-y-2">
    <p className="text-sm text-muted-foreground">{label} · Europe/Zurich</p>
    <ChartContainer config={{ value: { label, color: "var(--chart-2)" } }} className="h-80 w-full">
      <ComposedChart accessibilityLayer data={data}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="ts"
          tickFormatter={(ts: string) => formatChartLabel(ts, resolution)}
          minTickGap={32}
          tickLine={false}
        />
        <YAxis width={72} tickLine={false} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(ts) => formatChartLabel(String(ts), resolution)}
            />
          }
        />
        {kind === "bar"
          ? <Bar dataKey="value" fill="var(--color-value)" radius={2} isAnimationActive={false} />
          : <Line dataKey="value" stroke="var(--color-value)" strokeWidth={2} dot={data.length === 1} isAnimationActive={false} />}
      </ComposedChart>
    </ChartContainer>
  </div>;
}
