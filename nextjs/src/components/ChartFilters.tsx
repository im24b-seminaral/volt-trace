"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { datePresets, dateRangeError, maxDetailDays, presetRange, rangeDays, sensorColor, sensorDateRange } from "@/lib/chart-filters";
import type { Sensor } from "@/lib/types";

export default function ChartFilters({ dataset, sensors, selected, kind, from, to, resolution }: {
  dataset: string; sensors: Sensor[]; selected: string[]; kind: string; from: string; to: string; resolution: string;
}) {
  const [chartKind, setChartKind] = useState(kind);
  const { first, last } = sensorDateRange(sensors, chartKind);
  const [start, setStart] = useState(from || first);
  const [end, setEnd] = useState(to || last);
  const error = dateRangeError(start, end, first, last);
  const days = rangeDays(start, end);
  const activePreset = start === first && end === last ? "Alles" : datePresets.find((preset) => {
    const range = presetRange(preset, end, first, last);
    return start === range.from && end === range.to;
  });
  const submit = (form: HTMLFormElement | null) => requestAnimationFrame(() => form?.requestSubmit());

  return <>
    <input type="hidden" name="dataset" value={dataset} />
    <div className="flex flex-col gap-3">
      <div className="flex items-end gap-3">
      <div className="space-y-1.5"><Label htmlFor="kind">Diagramm</Label>
        <NativeSelect id="kind" name="kind" value={chartKind} disabled={!sensors.length} onChange={(event) => {
          const next = event.target.value;
          const range = sensorDateRange(sensors, next);
          setChartKind(next); setStart(range.first); setEnd(range.last);
          submit(event.currentTarget.form);
        }}>
          <NativeSelectOption value="consumption">Verbrauch</NativeSelectOption>
          <NativeSelectOption value="meter-reading">Zählerstand</NativeSelectOption>
        </NativeSelect>
      </div>
      {/* FA-08: Auflösung nur für Verbrauch; ESL-Zählerstände werden nie aggregiert. */}
      {chartKind === "consumption" ? <div className="space-y-1.5"><Label htmlFor="resolution">Auflösung</Label>
        <NativeSelect id="resolution" name="resolution" defaultValue={resolution} disabled={!sensors.length}>
          <NativeSelectOption value="day">Tag</NativeSelectOption>
          <NativeSelectOption value="15min" disabled={days > maxDetailDays}>
            {days > maxDetailDays ? `15 Minuten (max. ${maxDetailDays} Tage)` : "15 Minuten"}
          </NativeSelectOption>
        </NativeSelect>
      </div> : <input type="hidden" name="resolution" value={resolution} />}
      </div>
      <div className="flex flex-wrap items-end justify-end gap-3">
        <div className="space-y-1.5"><Label htmlFor="from">Von</Label>
          <Input id="from" name="from" type="date" className="w-40" value={start} required
            min={first} max={end || last} disabled={!sensors.length} aria-describedby={error ? "date-error" : undefined}
            onInput={(event) => setStart(event.currentTarget.value)} />
        </div>
        <div className="space-y-1.5"><Label htmlFor="to">Bis</Label>
          <Input id="to" name="to" type="date" className="w-40" value={end} required
            min={start || first} max={last} disabled={!sensors.length} aria-describedby={error ? "date-error" : undefined}
            onInput={(event) => setEnd(event.currentTarget.value)} />
        </div>
        <div className="flex flex-wrap gap-2">
          {datePresets.map((preset) => <Button key={preset} type="button"
            variant={activePreset === preset ? "secondary" : "outline"} aria-pressed={activePreset === preset}
            disabled={!last} onClick={(event) => {
              const range = presetRange(preset, end, first, last);
              setStart(range.from); setEnd(range.to); submit(event.currentTarget.form);
            }}>{preset}</Button>)}
        </div>
        {!error && <span className="py-1 text-sm text-muted-foreground">{days} {days === 1 ? "Tag" : "Tage"}</span>}
      </div>
    </div>
    {error && sensors.length > 0 && <p id="date-error" role="alert" className="text-sm text-destructive">{error}</p>}
    <p className="pt-2 text-sm text-muted-foreground">{chartKind === "consumption" ? "Verbrauch" : "Zählerstand"} (kWh) · Europe/Zurich</p>
    <div className="flex flex-wrap justify-center gap-4" role="group" aria-label="Sensoren">
      {sensors.map((sensor) => <Label key={sensor.sensorId} className="flex cursor-pointer items-center gap-2">
        <Checkbox name="sensor" value={sensor.sensorId} defaultChecked={selected.includes(sensor.sensorId)}
          style={{ borderColor: sensorColor(sensor.sensorId), backgroundColor: selected.includes(sensor.sensorId) ? sensorColor(sensor.sensorId) : undefined }} />
        {sensor.label}
      </Label>)}
    </div>
  </>;
}
