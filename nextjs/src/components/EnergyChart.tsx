"use client";

import { Bar, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent } from "@/components/ui/chart";
import { formatChartLabel, parseApiTimestamp } from "@/lib/datetime";
import type { SensorSeries } from "@/lib/types";

export default function EnergyChart({
  data,
  kind,
  resolution,
}: {
  data: SensorSeries[];
  kind: "bar" | "line";
  resolution: "day" | "15min";
}) {
  if (!data.some((series) => series.data.length)) return <p className="py-16 text-center text-muted-foreground">Keine Werte im Zeitraum.</p>;
  const label = kind === "bar" ? "Verbrauch (kWh)" : "Zählerstand (kWh)";
  const config = Object.fromEntries(data.map((series, index) => [series.sensorId,
    { label: series.sensorId, color: `var(--chart-${index % 5 + 1})` }]));
  const rows = new Map<number, Record<string, number>>();
  for (const series of data) for (const point of series.data) {
    const ts = parseApiTimestamp(point.ts).getTime();
    const row = rows.get(ts) ?? { ts };
    row[series.sensorId] = point.value;
    rows.set(ts, row);
  }
  const points = [...rows.values()].sort((a, b) => a.ts - b.ts);
  const formatTime = (ts: number) => formatChartLabel(new Date(ts).toISOString(), resolution);

  return <div className="space-y-2">
    <p className="text-sm text-muted-foreground">{label} · Europe/Zurich</p>
    <ChartContainer config={config} className="h-80 w-full">
      <ComposedChart accessibilityLayer data={points} margin={{ bottom: 20, left: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="ts"
          type={kind === "bar" ? "category" : "number"}
          scale={kind === "bar" ? "auto" : "time"} domain={["dataMin", "dataMax"]}
          tickFormatter={formatTime}
          minTickGap={32}
          tickLine={false}
          label={{ value: "Zeit (Europe/Zurich)", position: "insideBottom", offset: -15 }}
        />
        <YAxis width={72} tickLine={false} label={{ value: "kWh", angle: -90, position: "insideLeft" }} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(ts) => formatTime(Number(ts))}
            />
          }
        />
        <ChartLegend verticalAlign="top" content={<ChartLegendContent />} />
        {data.map((series) => kind === "bar"
          ? <Bar key={series.sensorId} dataKey={series.sensorId} stackId="consumption" fill={`var(--color-${series.sensorId})`} isAnimationActive={false} />
          : <Line key={series.sensorId} type="linear" dataKey={series.sensorId} connectNulls stroke={`var(--color-${series.sensorId})`} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />)}
      </ComposedChart>
    </ChartContainer>
  </div>;
}
