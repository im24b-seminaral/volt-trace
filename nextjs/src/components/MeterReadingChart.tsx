type MeterReadingChartProps = {
  hasReading: boolean;
};

export default function MeterReadingChart({ hasReading }: MeterReadingChartProps) {
  return (
    <p>
      {hasReading
        ? "Zählerstandsdiagramm folgt mit der API-Anbindung."
        : "Für diesen Sensor ist kein Zählerstand verfügbar."}
    </p>
  );
}
