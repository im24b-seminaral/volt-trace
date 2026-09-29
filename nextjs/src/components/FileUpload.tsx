import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = { busy: boolean; onFilesSelected: (files: File[]) => void };

export default function FileUpload({ busy, onFilesSelected }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);
  const selectFiles = (files: FileList | null) => {
    const xmlFiles = Array.from(files ?? []).filter((file) => file.name.toLowerCase().endsWith(".xml"));
    if (xmlFiles.length) onFilesSelected(xmlFiles);
  };
  return (
    <>
      <Input ref={input} className="hidden" type="file" accept=".xml" multiple
        onChange={(event) => {
          selectFiles(event.target.files);
          event.target.value = "";
        }} />
      <Input ref={folderInput} className="hidden" type="file" multiple {...{ webkitdirectory: "" }}
        onChange={(event) => {
          selectFiles(event.target.files);
          event.target.value = "";
        }} />
      <Button disabled={busy} onClick={() => input.current?.click()}>
        {busy ? "Lade hoch …" : "XML-Dateien wählen"}
      </Button>
      <Button variant="outline" disabled={busy} onClick={() => folderInput.current?.click()}>Ordner wählen</Button>
    </>
  );
}
