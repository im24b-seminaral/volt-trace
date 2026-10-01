// longtasks_konsole.js - Misst, ob die Oberfläche länger als 1 s blockiert (L-04).
//
// So benutzt du es (nur Chrome/Edge, Firefox und Safari kennen "longtask" nicht):
//   1. Seite http://localhost:3000 öffnen, F12 → Tab "Console".
//   2. Diesen ganzen Text hineinkopieren, Enter.
//   3. Jetzt hochladen, Sensor/Zeitraum/Diagramm wechseln, exportieren.
//   4. Am Schluss in der Konsole eingeben:   abnahmeErgebnis()
//      und die Ausgabe ins Testprotokoll kopieren.
//
// Ein "Long Task" ist eine Zeit, in der der Browser mit JavaScript beschäftigt ist
// und nicht auf Klicks reagieren kann. Grenze laut Issue: keine Blockade > 1000 ms.

window.__abnahmeLongTasks = [];
new PerformanceObserver((liste) => {
  for (const eintrag of liste.getEntries()) {
    const ms = Math.round(eintrag.duration);
    window.__abnahmeLongTasks.push({ ms, um: new Date().toLocaleTimeString("de-CH") });
    if (ms > 1000) console.warn(`❌ BLOCKADE ${ms} ms (> 1000 ms)`);
    else console.log(`Long Task ${ms} ms`);
  }
}).observe({ type: "longtask", buffered: true });

window.abnahmeErgebnis = () => {
  const alle = window.__abnahmeLongTasks;
  const max = alle.length ? Math.max(...alle.map((t) => t.ms)) : 0;
  const text =
    `L-04 UI-Blockade: ${alle.length} Long Tasks, längster ${max} ms → ` +
    (max > 1000 ? "❌ nicht bestanden" : "✅ bestanden") +
    ` (Grenze 1000 ms, gemessen ${new Date().toLocaleString("de-CH")}, ${navigator.userAgent})`;
  console.log(text);
  return text;
};

console.log("✅ Long-Task-Messung läuft. Am Schluss: abnahmeErgebnis()");
