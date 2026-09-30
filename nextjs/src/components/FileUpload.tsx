"use client";

import { useActionState, useRef } from "react";
import { uploadDataset } from "@/app/actions";
import { Button } from "@/components/ui/button";

export default function FileUpload() {
  const [error, action, pending] = useActionState(uploadDataset, "");
  const files = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);
  return <form action={action} className="space-y-2">
    <div className="flex flex-wrap gap-2">
      <input ref={files} hidden name="files" type="file" accept=".xml" multiple onChange={(e) => {
        if (folder.current) folder.current.value = "";
        if (e.target.files?.length) e.target.form?.requestSubmit();
      }} />
      <input ref={folder} hidden name="folder" type="file" multiple {...{ webkitdirectory: "" }} onChange={(e) => {
        if (files.current) files.current.value = "";
        if (e.target.files?.length) e.target.form?.requestSubmit();
      }} />
      <Button type="button" disabled={pending} onClick={() => files.current?.click()}>{pending ? "Lade hoch …" : "XML-Dateien wählen"}</Button>
      <Button type="button" variant="outline" disabled={pending} onClick={() => folder.current?.click()}>Ordner wählen</Button>
    </div>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
  </form>;
}
