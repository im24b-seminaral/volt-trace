"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import type { DataPoint } from "@/lib/types";

const config = { value: { label: "Verbrauch (kWh)", color: "var(--chart-2)" } } satisfies ChartConfig;

export default function ConsumptionChart({ data }: { data: DataPoint[] }) {
  if (!data.length) return <p className="py-16 text-center text-muted-foreground">Keine Werte im Zeitraum.</p>;
  return (
    <ChartContainer config={config} className="h-[320px] w-full">
      <BarChart accessibilityLayer data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="ts" tickFormatter={(ts: string) => ts.slice(5, 10)} tickLine={false} />
        <YAxis width={54} tickLine={false} />
        <ChartTooltip content={<ChartTooltipContent labelFormatter={(label) => String(label).slice(0, 16)} />} />
        <Bar dataKey="value" fill="var(--color-value)" radius={2} />
      </BarChart>
    </ChartContainer>
  );
}
