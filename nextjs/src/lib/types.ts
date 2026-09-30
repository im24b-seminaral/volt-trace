export type Sensor = { sensorId: string; label: string; hasMeterReadings: boolean };
export type DataPoint = { ts: string; value: number };
export type SensorSeries = { sensorId: string; data: DataPoint[] };
