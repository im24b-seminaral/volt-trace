type FileUploadProps = {
  onFilesSelected: (files: FileList) => void;
};

export default function FileUpload({ onFilesSelected }: FileUploadProps) {
  return (
    <div className="toolbar">
      <label className="file-button">
        XML-Dateien wählen
        <input
          type="file"
          accept=".xml,text/xml,application/xml"
          multiple
          onChange={(event) => {
            if (event.target.files?.length) onFilesSelected(event.target.files);
          }}
        />
      </label>
      <span className="hint">Upload noch nicht mit der Python-API verbunden.</span>
    </div>
  );
}
