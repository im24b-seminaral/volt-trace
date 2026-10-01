import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  formatChartDate,
  formatChartDateTime,
  formatChartLabel,
  localDayBoundsToUtcIso,
  localNextDayStartUtcIso,
  parseApiTimestamp,
} from "@/lib/datetime";
import { autumnDoubleHour, consumption15min, consumption15minSummer, springGap } from "./fixtures";

describe("Zeitachse Europe/Zurich", () => {
  it("zeigt den Tagesbeginn als lokales Datum (Winter und Sommer)", () => {
    assert.equal(formatChartDate("2018-12-31T23:00:00+00:00"), "01.01.2019");
    assert.equal(formatChartDate("2019-06-30T22:00:00+00:00"), "01.07.2019");
  });

  it("zeigt 15-Minuten-Werte im Winter mit +1", () => {
    assert.deepEqual(consumption15min.map((p) => formatChartDateTime(p.ts)), [
      "01.01.2018, 00:15 GMT+1",
      "01.01.2018, 00:30 GMT+1",
      "01.01.2018, 00:45 GMT+1",
    ]);
  });

  it("zeigt 15-Minuten-Werte im Sommer mit +2", () => {
    assert.deepEqual(consumption15minSummer.map((p) => formatChartDateTime(p.ts)), [
      "01.07.2019, 12:00 GMT+2",
      "01.07.2019, 12:15 GMT+2",
    ]);
  });

  it("unterscheidet die wiederholte Herbst-Doppelstunde über den UTC-Versatz", () => {
    const labels = autumnDoubleHour.map((p) => formatChartLabel(p.ts, "15min"));
    assert.equal(new Set(labels).size, autumnDoubleHour.length);
    assert.equal(labels[2], "27.10.2019, 02:30 GMT+2");
    assert.equal(labels[6], "27.10.2019, 02:30 GMT+1");
  });

  it("springt bei der Frühlings-Umstellung von 01:45 auf 03:00", () => {
    assert.deepEqual(springGap.map((p) => formatChartLabel(p.ts, "15min")), [
      "31.03.2019, 01:45 GMT+1",
      "31.03.2019, 03:00 GMT+2",
    ]);
  });

  it("wählt das Format nach Auflösung", () => {
    assert.equal(formatChartLabel("2019-10-27T00:30:00Z", "day"), "27.10.2019");
    assert.equal(formatChartLabel("2019-10-27T00:30:00Z", "15min"), "27.10.2019, 02:30 GMT+2");
  });
});

describe("parseApiTimestamp", () => {
  it("liest ts ohne Offset als UTC", () => {
    assert.equal(parseApiTimestamp("2019-01-01T00:00:00").toISOString(), "2019-01-01T00:00:00.000Z");
    assert.equal(parseApiTimestamp("2019-01-01T00:00:00+00:00").toISOString(), "2019-01-01T00:00:00.000Z");
  });

  it("lehnt ungültige Zeitstempel ab", () => {
    assert.throws(() => parseApiTimestamp("kein-datum"), /Ungültiger Zeitstempel/);
  });
});

describe("localDayBoundsToUtcIso", () => {
  it("liefert den lokalen Tagesbeginn im Winter, Sommer und an Umstellungstagen", () => {
    assert.equal(localDayBoundsToUtcIso("2019-01-01").from, "2018-12-31T23:00:00.000Z");
    assert.equal(localDayBoundsToUtcIso("2019-07-01").from, "2019-06-30T22:00:00.000Z");
    assert.equal(localDayBoundsToUtcIso("2019-10-27").from, "2019-10-26T22:00:00.000Z");
    assert.equal(localDayBoundsToUtcIso("2019-03-31").from, "2019-03-30T23:00:00.000Z");
  });

  it("liefert lokale Tagesgrenzen im Winter und Sommer", () => {
    assert.deepEqual(localDayBoundsToUtcIso("2019-01-01"), {
      from: "2018-12-31T23:00:00.000Z",
      to: "2019-01-01T22:59:59.999Z",
    });
    assert.deepEqual(localDayBoundsToUtcIso("2019-07-01"), {
      from: "2019-06-30T22:00:00.000Z",
      to: "2019-07-01T21:59:59.999Z",
    });
  });

  it("deckt den 25-Stunden-Tag im Herbst und den 23-Stunden-Tag im Frühling ab", () => {
    assert.deepEqual(localDayBoundsToUtcIso("2019-10-27"), {
      from: "2019-10-26T22:00:00.000Z",
      to: "2019-10-27T22:59:59.999Z",
    });
    assert.deepEqual(localDayBoundsToUtcIso("2019-03-31"), {
      from: "2019-03-30T23:00:00.000Z",
      to: "2019-03-31T21:59:59.999Z",
    });
  });

  it("lehnt ungültige Daten ab", () => {
    assert.throws(() => localDayBoundsToUtcIso(""), /Ungültiges Datum/);
  });

  it("nimmt beim SDAT-Verbrauch das Intervallende an der nächsten Mitternacht mit", () => {
    assert.equal(localNextDayStartUtcIso("2019-01-01"), "2019-01-01T23:00:00.000Z");
    assert.equal(localNextDayStartUtcIso("2019-10-27"), "2019-10-27T23:00:00.000Z");
    assert.equal(localNextDayStartUtcIso("2019-03-31"), "2019-03-31T22:00:00.000Z");
  });
});
