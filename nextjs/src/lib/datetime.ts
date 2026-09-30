export const DISPLAY_TZ = "Europe/Zurich";

const dateFormatter = new Intl.DateTimeFormat("de-CH", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  timeZone: DISPLAY_TZ,
});

const timeFormatter = new Intl.DateTimeFormat("de-CH", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: DISPLAY_TZ,
});

const dateTimeWithOffsetFormatter = new Intl.DateTimeFormat("de-CH", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: DISPLAY_TZ,
  timeZoneName: "shortOffset",
});

const zurichPartsFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: DISPLAY_TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

/** Python isoformat (UTC); fehlender Offset wird als UTC interpretiert. */
export function parseApiTimestamp(ts: string): Date {
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/i.test(ts) ? ts : `${ts}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) throw new Error(`Ungültiger Zeitstempel: ${ts}`);
  return date;
}

export function formatChartDate(ts: string): string {
  return dateFormatter.format(parseApiTimestamp(ts));
}

export function formatChartDateTime(ts: string): string {
  const date = parseApiTimestamp(ts);
  return dateTimeWithOffsetFormatter.format(date);
}

export function formatChartLabel(ts: string, resolution: "day" | "15min"): string {
  return resolution === "day" ? formatChartDate(ts) : formatChartDateTime(ts);
}

/** Lokale Uhrzeit in Europe/Zurich als UTC-Instant. */
function zurichLocalToUtc(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
  second: number,
  millisecond: number,
): Date {
  let utcMs = Date.UTC(year, month - 1, day, hour, minute, second, millisecond);
  const wanted = Date.UTC(year, month - 1, day, hour, minute, second, millisecond);

  for (let i = 0; i < 4; i++) {
    const parts = Object.fromEntries(
      zurichPartsFormatter.formatToParts(new Date(utcMs)).map((p) => [p.type, p.value]),
    );
    const shown = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
      Number(parts.second),
    );
    utcMs += wanted - shown;
  }

  return new Date(utcMs);
}

/**
 * Kalendertag (HTML date input YYYY-MM-DD) als Tagesgrenzen in Europe/Zurich,
 * zurückgegeben als ISO-UTC-Strings für die Python-API.
 */
export function localDayBoundsToUtcIso(dateYmd: string): { from: string; to: string } {
  const [y, m, d] = dateYmd.split("-").map(Number);
  if (!y || !m || !d) throw new Error(`Ungültiges Datum: ${dateYmd}`);

  const from = zurichLocalToUtc(y, m, d, 0, 0, 0, 0);
  const to = zurichLocalToUtc(y, m, d, 23, 59, 59, 999);

  return { from: from.toISOString(), to: to.toISOString() };
}
