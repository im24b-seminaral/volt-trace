"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileArchive, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import UploadProgress, { stepIndex, type StepId, type UploadState } from "@/components/UploadProgress";

type ServerEvent = { step?: StepId; done?: number; total?: number; dataset?: string; error?: string };

function setFolderPaths(form: HTMLFormElement, selected: FileList | null) {
  form.querySelectorAll("input[data-folder-path]").forEach((input) => input.remove());
  Array.from(selected ?? []).forEach((file) => {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = "folderPath";
    input.value = file.webkitRelativePath || file.name;
    input.dataset.folderPath = "";
    form.append(input);
  });
}

function Tile({ icon: Icon, title, hint, onClick }: {
  icon: typeof FolderOpen; title: string; hint: string; onClick: () => void;
}) {
  return <button type="button" onClick={onClick}
    className="flex flex-col items-center gap-2 rounded-xl border border-dashed p-8 text-center outline-ring/50 transition-colors hover:border-ring hover:bg-accent focus-visible:outline-2">
    <Icon aria-hidden className="size-8 text-muted-foreground" />
    <span className="font-medium">{title}</span>
    <span className="text-sm text-muted-foreground">{hint}</span>
  </button>;
}

export default function FileUpload({ variant = "toolbar" }: { variant?: "toolbar" | "start" }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [upload, setUpload] = useState<UploadState | null>(null);
  const files = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);

  function send(form: HTMLFormElement) {
    setError("");
    setUpload({ startedAt: Date.now(), index: 0, values: {} });

    const show = (step: StepId, done: number, total: number) => setUpload((state) => state && {
      ...state,
      index: Math.max(state.index, stepIndex(step)),
      values: { ...state.values, [step]: { done, total } },
    });

    let finished = false;
    const request = new XMLHttpRequest();
    const read = () => {
      if (finished) return;
      const lines = request.responseText.split("\n");
      lines.pop();   // die letzte Zeile kann noch unvollständig sein
      if (!lines.length) return;
      const event: ServerEvent = JSON.parse(lines[lines.length - 1]);
      if (event.step) show(event.step, event.done ?? 0, event.total ?? 0);
      else if (event.error) { finished = true; setUpload(null); setError(event.error); }
      else if (event.dataset) {
        finished = true;
        // Die Karte bleibt stehen, bis der Importbericht gerendert ist.
        router.push(`/import/${event.dataset}`);
      }
    };

    request.open("POST", "/api/upload");
    request.upload.onprogress = (event) => show("transfer", event.loaded, event.total);
    request.onprogress = read;
    request.onload = () => {
      read();
      if (!finished) { setUpload(null); setError("Der Import wurde unerwartet beendet. Bitte erneut versuchen."); }
    };
    request.onerror = () => { setUpload(null); setError("Verbindung zum Server verloren. Bitte erneut versuchen."); };
    request.send(new FormData(form));
  }

  if (upload) return <UploadProgress state={upload} />;

  return <form onSubmit={(event) => { event.preventDefault(); send(event.currentTarget); }} className="space-y-2">
    <input ref={files} hidden name="files" type="file" accept=".xml,.zip" multiple onChange={(e) => {
      if (folder.current) folder.current.value = "";
      if (e.target.form) setFolderPaths(e.target.form, null);
      if (e.target.files?.length) e.target.form?.requestSubmit();
    }} />
    <input ref={folder} hidden name="folder" type="file" multiple {...{ webkitdirectory: "" }} onChange={(e) => {
      if (files.current) files.current.value = "";
      if (e.target.form) setFolderPaths(e.target.form, e.target.files);
      if (e.target.files?.length) e.target.form?.requestSubmit();
    }} />
    {variant === "start"
      ? <div className="grid gap-4 sm:grid-cols-2">
          <Tile icon={FolderOpen} title="Ordner wählen" hint="Ganzen Ordner mit XML-Dateien einlesen"
            onClick={() => folder.current?.click()} />
          <Tile icon={FileArchive} title="ZIP hochladen" hint="ZIP-Archiv oder einzelne XML-Dateien"
            onClick={() => files.current?.click()} />
        </div>
      : <div className="flex flex-wrap gap-2">
          <Button type="button" onClick={() => files.current?.click()}>XML/ZIP-Dateien wählen</Button>
          <Button type="button" variant="outline" onClick={() => folder.current?.click()}>Ordner wählen</Button>
        </div>}
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
  </form>;
}
