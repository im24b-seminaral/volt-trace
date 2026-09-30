import EnergyChart from "@/components/EnergyChart";
import type { DataPoint } from "@/lib/types";

export default function MeterReadingChart({
  data,
  resolution,
}: {
  data: DataPoint[];
  resolution: "day" | "15min";
}) {
  return <EnergyChart data={data} kind="line" resolution={resolution} />;
}
