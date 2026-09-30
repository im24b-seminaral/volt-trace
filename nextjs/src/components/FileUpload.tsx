"use client";

import { useActionState, useRef } from "react";
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

export default function FileUpload() {
  const [error, action, pending] = useActionState(uploadDataset, "");
  const files = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);
  return <form action={action} className="space-y-2">
    <div className="flex flex-wrap gap-2">
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
      <Button type="button" disabled={pending} onClick={() => files.current?.click()}>{pending ? "Lade hoch …" : "XML/ZIP-Dateien wählen"}</Button>
      <Button type="button" variant="outline" disabled={pending} onClick={() => folder.current?.click()}>Ordner wählen</Button>
    </div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
  </form>;
}
