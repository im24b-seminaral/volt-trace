// Feste UTC-Daten im Format der Python-CLI (series): ts = ISO-8601 in UTC, Werte bereits berechnet.
import type { DataPoint } from "@/lib/types";

/** Tagesverbrauch: Tagesbeginn Europe/Zurich als UTC (Winter 23:00Z, Sommer 22:00Z). */
export const consumptionDay: DataPoint[] = [
  { ts: "2018-12-31T23:00:00+00:00", value: 96.9 },
  { ts: "2019-01-01T23:00:00+00:00", value: 101.25 },
  { ts: "2019-06-30T22:00:00+00:00", value: 54.1 },
];

/** 15-Minuten-Verbrauch im Winter, ts = Intervallende (FA-05). */
export const consumption15min: DataPoint[] = [
  { ts: "2017-12-31T23:15:00+00:00", value: 2.7 },
  { ts: "2017-12-31T23:30:00+00:00", value: 2.5 },
  { ts: "2017-12-31T23:45:00+00:00", value: 2.6 },
];

/** 15-Minuten-Verbrauch im Sommer (UTC+2). */
export const consumption15minSummer: DataPoint[] = [
  { ts: "2019-07-01T10:00:00+00:00", value: 1.1 },
  { ts: "2019-07-01T10:15:00+00:00", value: 1.3 },
];

/** Herbst-Doppelstunde 27.10.2019: lokal 02:00–02:45 kommt zweimal vor (zuerst +02:00, dann +01:00). */
export const autumnDoubleHour: DataPoint[] = [
  "2019-10-27T00:00:00Z", "2019-10-27T00:15:00Z", "2019-10-27T00:30:00Z", "2019-10-27T00:45:00Z",
  "2019-10-27T01:00:00Z", "2019-10-27T01:15:00Z", "2019-10-27T01:30:00Z", "2019-10-27T01:45:00Z",
].map((ts, i) => ({ ts, value: 0.5 + i / 10 }));

/** Frühlings-Umstellung 31.03.2019: auf 01:45 (+01:00) folgt direkt 03:00 (+02:00). */
export const springGap: DataPoint[] = [
  { ts: "2019-03-31T00:45:00Z", value: 0.4 },
  { ts: "2019-03-31T01:00:00Z", value: 0.3 },
];

/** ESL-Monatsstände ID742 (unregelmässige Abstände, Winter und Sommer). */
export const eslMonthly: DataPoint[] = [
  { ts: "2018-12-31T23:00:00+00:00", value: 19216.2 },
  { ts: "2019-01-31T23:00:00+00:00", value: 21052.8 },
  { ts: "2019-02-28T23:00:00+00:00", value: 23468.7 },
  { ts: "2019-06-30T22:00:00+00:00", value: 30217.4 },
];

export const empty: DataPoint[] = [];
