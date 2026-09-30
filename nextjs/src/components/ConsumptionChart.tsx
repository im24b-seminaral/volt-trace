import EnergyChart from "@/components/EnergyChart";
import type { DataPoint } from "@/lib/types";

export default function ConsumptionChart({
  data,
  resolution,
}: {
  data: DataPoint[];
  resolution: "day" | "15min";
}) {
  return <EnergyChart data={data} kind="bar" resolution={resolution} />;
}
