import EnergyChart from "@/components/EnergyChart";
import type { DataPoint } from "@/lib/types";

export default function MeterReadingChart({ data }: { data: DataPoint[] }) {
  return <EnergyChart data={data} kind="line" />;
}
