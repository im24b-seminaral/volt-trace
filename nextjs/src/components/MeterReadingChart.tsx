"use client";

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import type { DataPoint } from "@/lib/python";

const config = { value: { label: "Zählerstand (kWh)", color: "var(--chart-3)" } } satisfies ChartConfig;

export default function MeterReadingChart({ data }: { data: DataPoint[] }) {
  if (!data.length) return <p className="py-16 text-center text-muted-foreground">Keine Zählerstände im Zeitraum.</p>;
  return (
    <ChartContainer config={config} className="h-[320px] w-full">
      <LineChart accessibilityLayer data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="ts" tickFormatter={(ts: string) => ts.slice(5, 10)} tickLine={false} />
        <YAxis width={72} domain={["dataMin", "dataMax"]} tickLine={false} />
        <ChartTooltip content={<ChartTooltipContent labelFormatter={(label) => String(label).slice(0, 16)} />} />
        <Line dataKey="value" stroke="var(--color-value)" dot={false} strokeWidth={2} />
      </LineChart>
    </ChartContainer>
  );
}
