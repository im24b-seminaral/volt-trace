import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  AppRouterContext,
  type AppRouterInstance,
} from "next/dist/shared/lib/app-router-context.shared-runtime";
import { Bar, ComposedChart, Line, XAxis, YAxis } from "recharts";

import ChartForm from "@/components/ChartForm";
import ConsumptionChart from "@/components/ConsumptionChart";
import EnergyChart from "@/components/EnergyChart";
import MeterReadingChart from "@/components/MeterReadingChart";
import { ChartTooltipContent } from "@/components/ui/chart";
import type { DataPoint } from "@/lib/types";
import {
  autumnDoubleHour,
  consumption15min,
  consumptionDay,
  empty,
  eslMonthly,
} from "./fixtures";
import { findAll, findOne } from "./tree";

type Formatter = (value: number) => string;

const chart = (data: DataPoint[], kind: "bar" | "line", resolution: "day" | "15min") =>
  EnergyChart({ data: [{ sensorId: "ID742", data }], kind, resolution }) as ReactNode;

describe("ConsumptionChart / MeterReadingChart", () => {
  it("Verbrauch wird als Balken weitergegeben, unverändert", () => {
    const element = ConsumptionChart({ data: [{ sensorId: "ID742", data: consumptionDay }], resolution: "day" });
    assert.equal(element.type, EnergyChart);
    assert.equal(element.props.kind, "bar");
    assert.equal(element.props.resolution, "day");
    assert.equal(element.props.data[0].data, consumptionDay);
  });

  it("Zählerstände werden als Linie weitergegeben, unverändert", () => {
    const element = MeterReadingChart({ data: [{ sensorId: "ID742", data: eslMonthly }], resolution: "day" });
    assert.equal(element.type, EnergyChart);
    assert.equal(element.props.kind, "line");
    assert.equal(element.props.data[0].data, eslMonthly);
  });
});

describe("EnergyChart", () => {
  it("aligns two sensors by timestamp and stacks consumption, without inventing missing readings", () => {
    const data = [
      { sensorId: "ID742", data: consumptionDay },
      { sensorId: "ID735", data: consumptionDay.slice(1).map((p) => ({ ...p, value: 2 })) },
    ];
    const tree = EnergyChart({ data, kind: "bar", resolution: "day" });
    const bars = findAll(tree, Bar);
    assert.equal(bars.length, 2);
    assert.equal(bars[0].props.stackId, bars[1].props.stackId);
    const rows = findOne(tree, ComposedChart).props.data as Record<string, number>[];
    assert.equal(rows.length, 3);
    assert.equal(rows[0].ID735, undefined);
    assert.equal(rows[1].ID735, 2);
    assert.equal(rows[1].ID742, consumptionDay[1].value);
    const lines = findAll(EnergyChart({ data, kind: "line", resolution: "day" }), Line);
    assert.equal(lines.length, 2);
    assert.notEqual(lines[0].props.stroke, lines[1].props.stroke);
  });
  it("zeigt Tagesverbrauch als Balken ohne Neuberechnung", () => {
    const tree = chart(consumptionDay, "bar", "day");
    assert.deepEqual(findOne(tree, ComposedChart).props.data, consumptionDay.map((p) => ({ ts: Date.parse(p.ts), ID742: p.value })));
    assert.equal(findOne(tree, Bar).props.dataKey, "ID742");
    assert.equal(findAll(tree, Line).length, 0);
  });

  it("zeigt 15-Minuten-Verbrauch als Balken", () => {
    const tree = chart(consumption15min, "bar", "15min");
    assert.deepEqual(findOne(tree, ComposedChart).props.data, consumption15min.map((p) => ({ ts: Date.parse(p.ts), ID742: p.value })));
    assert.equal(findAll(tree, Bar).length, 1);
  });

  it("markiert jeden ESL-Stand und verbindet ihn linear, ohne Zwischenpunkte", () => {
    const tree = chart(eslMonthly, "line", "day");
    const line = findOne(tree, Line);
    assert.equal(line.props.type, "linear");
    assert.equal(line.props.dataKey, "ID742");
    assert.deepEqual(line.props.dot, { r: 3 });
    assert.equal(findAll(tree, Bar).length, 0);
    // Genau die übergebenen Punkte, keine erfundenen Zwischenmessungen.
    assert.deepEqual(findOne(tree, ComposedChart).props.data, eslMonthly.map((p) => ({ ts: Date.parse(p.ts), ID742: p.value })));
    assert.equal(eslMonthly.length, 4);
  });

  it("beschriftet Zeitachse (Europe/Zurich) und Wertachse (kWh)", () => {
    const tree = chart(eslMonthly, "line", "day");
    const xAxis = findOne(tree, XAxis);
    assert.equal(xAxis.props.dataKey, "ts");
    assert.equal((xAxis.props.label as { value: string }).value, "Zeit (Europe/Zurich)");
    assert.equal((findOne(tree, YAxis).props.label as { value: string }).value, "kWh");
  });

  it("formatiert ESL-Monatswerte als lokale Tage", () => {
    const tick = findOne(chart(eslMonthly, "line", "day"), XAxis).props.tickFormatter as Formatter;
    assert.deepEqual(eslMonthly.map((p) => tick(Date.parse(p.ts))), ["01.01.2019", "01.02.2019", "01.03.2019", "01.07.2019"]);
  });

  it("macht die Herbst-Doppelstunde in Achse und Tooltip unterscheidbar", () => {
    const tree = chart(autumnDoubleHour, "bar", "15min");
    const tick = findOne(tree, XAxis).props.tickFormatter as Formatter;
    const tooltip = findOne(tree, ChartTooltipContent).props.labelFormatter as Formatter;
    for (const format of [tick, tooltip]) {
      const labels = autumnDoubleHour.map((p) => format(Date.parse(p.ts)));
      assert.equal(new Set(labels).size, autumnDoubleHour.length);
      assert.ok(labels.includes("27.10.2019, 02:00 GMT+2"));
      assert.ok(labels.includes("27.10.2019, 02:00 GMT+1"));
    }
  });

  it("nennt Grösse und Zeitzone über dem Diagramm", () => {
    assert.match(renderToStaticMarkup(chart(consumptionDay, "bar", "day")), /Verbrauch \(kWh\) · Europe\/Zurich/);
    assert.match(renderToStaticMarkup(chart(eslMonthly, "line", "day")), /Zählerstand \(kWh\) · Europe\/Zurich/);
  });

  it("zeigt bei leerer Reihe einen verständlichen Hinweis statt eines leeren Diagramms", () => {
    for (const kind of ["bar", "line"] as const) {
      const tree = chart(empty, kind, "day");
      assert.equal(findAll(tree, ComposedChart).length, 0);
      assert.match(renderToStaticMarkup(tree), /Keine Werte im Zeitraum\./);
    }
  });
});

describe("ChartForm", () => {
  // Test-Double: im Ruhezustand ruft ChartForm den Router nicht auf.
  const router = {
    push() {}, replace() {}, refresh() {}, back() {}, forward() {}, prefetch() {},
  } as unknown as AppRouterInstance;

  it("bleibt im Ruhezustand bedienbar und zeigt das Diagramm", () => {
    const html = renderToStaticMarkup(
      <AppRouterContext.Provider value={router}>
        <ChartForm chart={<p>Diagramm</p>}><select name="kind" /></ChartForm>
      </AppRouterContext.Provider>,
    );
    assert.match(html, /<fieldset class="[^"]*">/);
    assert.doesNotMatch(html, /<fieldset[^>]*disabled/);
    assert.match(html, /<select name="kind">/);
    assert.match(html, /aria-busy="false"><p>Diagramm<\/p>/);
    assert.doesNotMatch(html, /Diagramm wird geladen/);
  });
});
