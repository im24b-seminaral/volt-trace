import EnergyChart from "@/components/EnergyChart";
import type { SensorSeries } from "@/lib/types";

export default function ConsumptionChart({
  data,
  resolution,
}: {
  data: SensorSeries[];
  resolution: "day" | "15min";
}) {
  return <EnergyChart data={data} kind="bar" resolution={resolution} />;
}
