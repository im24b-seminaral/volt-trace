const sample = [32, 28, 31, 25, 27, 33, 35, 30, 27, 32, 37, 35, 31, 25];

export default function ConsumptionChart() {
  return (
    <>
      <div className="chart-label">Verbrauch (kWh)</div>
      <div className="bars">
        {sample.map((value, index) => (
          <div className="bar-item" key={index}>
            <div
              className="bar"
              style={{ height: `${(value / 40) * 100}%` }}
              title={`${index + 1}. Juni: ${value} kWh`}
            />
            <span>{index + 1}</span>
          </div>
        ))}
      </div>
      <div className="chart-label bottom">Juni 2020 · Beispieldaten</div>
    </>
  );
}
