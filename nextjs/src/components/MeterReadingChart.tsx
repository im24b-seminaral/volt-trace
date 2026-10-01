import EnergyChart from "@/components/EnergyChart";
import type { SensorSeries } from "@/lib/types";

export default function MeterReadingChart({
  data,
  resolution,
}: {
  data: SensorSeries[];
  resolution: "day" | "15min";
}) {
  return <EnergyChart data={data} kind="line" resolution={resolution} />;
}
