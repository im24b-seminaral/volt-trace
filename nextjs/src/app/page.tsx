"use client";

import { useState } from "react";
import FileUpload from "@/components/FileUpload";
import ConsumptionChart from "@/components/ConsumptionChart";
import MeterReadingChart from "@/components/MeterReadingChart";

type View = "consumption" | "meter-reading";
type Status = "preview" | "empty" | "loading" | "error";

const sensors = [
  { id: "ID742", name: "Netzbezug", hasReading: true },
  { id: "ID735", name: "Einspeisung", hasReading: true },
  { id: "ID26256", name: "ID26256", hasReading: false },
];

export default function Home() {
  const [view, setView] = useState<View>("consumption");
  const [status, setStatus] = useState<Status>("preview");
  const [sensorId, setSensorId] = useState("ID742");
  const [from, setFrom] = useState("2020-06-01");
  const [to, setTo] = useState("2020-06-14");
  const [resolution, setResolution] = useState("day");
  const sensor = sensors.find((item) => item.id === sensorId)!;

  return (
    <main>
      <h1>Messdaten</h1>
      <FileUpload onFilesSelected={() => setStatus("error")} />
      <div className="controls">
        <label>Sensor<select value={sensorId} onChange={(event) => setSensorId(event.target.value)}>
          {sensors.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.id})</option>)}
        </select></label>
        <label>Von<input type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
        <label>Bis<input type="date" value={to} onChange={(event) => setTo(event.target.value)} /></label>
        <label>Auflösung<select value={resolution} onChange={(event) => setResolution(event.target.value)}>
          <option value="day">Tag</option><option value="15min">15 Minuten</option>
        </select></label>
      </div>
      <div className="tabs" role="group" aria-label="Diagrammtyp">
        <button className={view === "consumption" ? "active" : ""} onClick={() => setView("consumption")}>Verbrauch</button>
        <button className={view === "meter-reading" ? "active" : ""} onClick={() => setView("meter-reading")}>Zählerstand</button>
      </div>
      <section className="chart" aria-label="Diagramm">
        {status === "error" ? <p role="alert">Die Dateien wurden nicht hochgeladen. Die Python-API ist noch nicht verbunden.</p>
          : status === "loading" ? <p role="status">Daten werden geladen …</p>
          : status === "empty" ? <p>Keine Daten vorhanden.</p>
          : view === "meter-reading" ? <MeterReadingChart hasReading={sensor.hasReading} />
          : <ConsumptionChart />}
      </section>
    </main>
  );
}
