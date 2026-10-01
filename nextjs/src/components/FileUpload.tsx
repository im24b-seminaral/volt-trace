"use client";

import { useActionState, useRef } from "react";
import { FileArchive, FolderOpen } from "lucide-react";
import { uploadDataset } from "@/app/actions";
import { Button } from "@/components/ui/button";

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

function Tile({ icon: Icon, title, hint, disabled, onClick }: {
  icon: typeof FolderOpen; title: string; hint: string; disabled: boolean; onClick: () => void;
}) {
  return <button type="button" disabled={disabled} onClick={onClick}
    className="flex flex-col items-center gap-2 rounded-xl border border-dashed p-8 text-center outline-ring/50 transition-colors hover:border-ring hover:bg-accent focus-visible:outline-2 disabled:pointer-events-none disabled:opacity-60">
    <Icon aria-hidden className="size-8 text-muted-foreground" />
    <span className="font-medium">{title}</span>
    <span className="text-sm text-muted-foreground">{hint}</span>
  </button>;
}

export default function FileUpload({ variant = "toolbar" }: { variant?: "toolbar" | "start" }) {
  const [error, action, pending] = useActionState(uploadDataset, "");
  const files = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);
  return <form action={action} className="space-y-2">
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
            disabled={pending} onClick={() => folder.current?.click()} />
          <Tile icon={FileArchive} title="ZIP hochladen" hint="ZIP-Archiv oder einzelne XML-Dateien"
            disabled={pending} onClick={() => files.current?.click()} />
        </div>
      : <div className="flex flex-wrap gap-2">
          <Button type="button" disabled={pending} onClick={() => files.current?.click()}>{pending ? "Lade hoch …" : "XML/ZIP-Dateien wählen"}</Button>
          <Button type="button" variant="outline" disabled={pending} onClick={() => folder.current?.click()}>Ordner wählen</Button>
        </div>}
    {variant === "start" && pending && <p role="status" className="text-center text-sm text-muted-foreground">Lade hoch …</p>}
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
  </form>;
}
