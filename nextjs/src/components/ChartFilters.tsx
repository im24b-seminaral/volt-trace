"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import type { Sensor } from "@/lib/types";

export default function ChartFilters({ dataset, sensors, selected, kind, from, to, first, last }: {
  dataset: string; sensors: Sensor[]; selected: string[]; kind: string;
  from: string; to: string; first: string; last: string;
}) {
  const [start, setStart] = useState(from || first);
  const [end, setEnd] = useState(to || last);
  const [preset, setPreset] = useState(from || to ? "" : "Alles");
  const days = Math.round((Date.parse(end || last) - Date.parse(start || first)) / 86400000) + 1;

  function selectRange(value: string) {
    setPreset(value);
    if (value === "Alles") { setStart(first); setEnd(last); return; }
    const date = new Date(end || last);
    if (!Number.isFinite(date.getTime())) return;
    setEnd(date.toISOString().slice(0, 10));
    if (value === "7 Tage") date.setUTCDate(date.getUTCDate() - 6);
    else {
      const day = date.getUTCDate();
      date.setUTCDate(1);
      date.setUTCMonth(date.getUTCMonth() - (value === "Monat" ? 1 : 12));
      const lastDay = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
      date.setUTCDate(Math.min(day, lastDay) + 1);
    }
    setStart(date.toISOString().slice(0, 10));
  }

  return <>
    <input type="hidden" name="dataset" value={dataset} />
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="space-y-1.5"><Label htmlFor="kind">Diagramm</Label>
        <NativeSelect id="kind" name="kind" defaultValue={kind} disabled={!dataset}>
          <NativeSelectOption value="consumption">Verbrauch</NativeSelectOption>
          <NativeSelectOption value="meter-reading">Zählerstand</NativeSelectOption>
        </NativeSelect>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-4" role="group" aria-label="Sensoren">
        {sensors.map((sensor) => <Label key={sensor.sensorId} className="flex items-center gap-2">
          <Checkbox name="sensor" value={sensor.sensorId} defaultChecked={selected.includes(sensor.sensorId)} />
          {sensor.label}
        </Label>)}
      </div>
    </div>
    <div className="flex flex-wrap items-end justify-end gap-3">
      <div className="space-y-1.5"><Label htmlFor="from">Von</Label>
        <Input id="from" name="from" type="date" className="w-40" value={start} max={end || undefined}
          disabled={!dataset} onChange={(event) => { setStart(event.target.value); setPreset(""); }} />
      </div>
      <div className="space-y-1.5"><Label htmlFor="to">Bis</Label>
        <Input id="to" name="to" type="date" className="w-40" value={end} min={start || undefined}
          disabled={!dataset} onChange={(event) => { setEnd(event.target.value); setPreset(""); }} />
      </div>
      <div className="flex flex-wrap gap-2">
        {["7 Tage", "Monat", "Jahr", "Alles"].map((value) => <Button key={value} type="button"
          variant={preset === value ? "secondary" : "outline"} aria-pressed={preset === value}
          disabled={!dataset || !last} onClick={() => selectRange(value)}>{value}</Button>)}
      </div>
      {Number.isFinite(days) && days > 0 && <span className="py-1 text-sm text-muted-foreground">{days} Tage</span>}
      <Button disabled={!dataset}>Anzeigen</Button>
    </div>
  </>;
}
