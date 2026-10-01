"""
HTTP-Oberfläche für den Python-Service (Vercel Services, intern über Binding).
"""

import io
import json
import shutil
from contextlib import redirect_stdout
from pathlib import Path
from typing import Annotated, Iterator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse

from volt_trace import cli
from volt_trace.cli import ExportError, export_payload
from volt_trace.data_paths import dataset_path
from volt_trace.progress import Progress

app = FastAPI(title="volt-trace-python", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _safe_upload_path(value: str) -> Path:
    parts = value.replace("\\", "/").split("/")
    if not parts or any(
        not part or part in (".", "..") or ":" in part or "\0" in part for part in parts
    ):
        raise HTTPException(status_code=400, detail="Ungültiger Dateipfad im Upload.")
    return Path(*parts)


def _dataset_dir(dataset_id: str) -> Path:
    try:
        return dataset_path(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/datasets/{dataset_id}/import")
async def import_dataset(
    dataset_id: str,
    files: Annotated[list[UploadFile], File()] = [],
    folder: Annotated[list[UploadFile], File()] = [],
    folder_path: Annotated[list[str], Form(alias="folderPath")] = [],
) -> StreamingResponse:
    incoming = [*files, *folder]
    upload_buffers = [await upload.read() for upload in incoming]
    destination = _dataset_dir(dataset_id)
    raw = Path(f"{destination}_raw")

    def body() -> Iterator[bytes]:
        try:
            raw.mkdir(parents=True, exist_ok=True)
            names: set[str] = set()
            yield (json.dumps({"step": "write", "done": 0, "total": len(incoming)}) + "\n").encode()
            for index, buffer in enumerate(upload_buffers):
                is_folder = index >= len(files)
                name_hint = (
                    folder_path[index - len(files)]
                    if is_folder and index - len(files) < len(folder_path)
                    else incoming[index].filename or "file"
                )
                relative = _safe_upload_path(name_hint)
                original = Path("folder" if is_folder else "files") / relative
                name = original.as_posix()
                suffix = 1
                while name.lower() in names:
                    parsed = original
                    name = str(parsed.parent / f"{parsed.stem}_{suffix}{parsed.suffix}").replace("\\", "/")
                    suffix += 1
                names.add(name.lower())
                target = raw / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(buffer)
                yield (json.dumps({"step": "write", "done": index + 1, "total": len(incoming)}) + "\n").encode()

            progress_lines: list[dict] = []
            progress = Progress(enabled=True, sink=progress_lines.append)
            report = cli.cmd_sort_files(str(raw), str(destination), progress=progress)
            for event in progress_lines:
                yield (json.dumps(event) + "\n").encode()
            (destination / "import-report.json").write_text(json.dumps(report), encoding="utf-8")
            yield (json.dumps(report) + "\n").encode()
        except HTTPException as exc:
            yield (json.dumps({"error": exc.detail}) + "\n").encode()
            shutil.rmtree(destination, ignore_errors=True)
        except Exception as exc:
            yield (json.dumps({"error": str(exc)}) + "\n").encode()
            shutil.rmtree(destination, ignore_errors=True)
        finally:
            shutil.rmtree(raw, ignore_errors=True)

    return StreamingResponse(body(), media_type="application/x-ndjson; charset=utf-8")


@app.delete("/v1/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, bool]:
    root = _dataset_dir(dataset_id)
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(Path(f"{root}_raw"), ignore_errors=True)
    return {"ok": True}


@app.get("/v1/datasets/{dataset_id}/import-report")
def get_import_report(dataset_id: str) -> dict:
    report_path = _dataset_dir(dataset_id) / "import-report.json"
    if not report_path.is_file():
        raise HTTPException(status_code=404, detail="Importbericht nicht gefunden.")
    return json.loads(report_path.read_text(encoding="utf-8"))


@app.get("/v1/datasets/{dataset_id}/sensors")
def list_sensors(dataset_id: str) -> Response:
    directory = str(_dataset_dir(dataset_id))
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        cli.cmd_sensors(directory)
    return Response(content=buffer.getvalue(), media_type="application/json")


@app.get("/v1/datasets/{dataset_id}/series")
def series(
    dataset_id: str,
    sensor_id: str,
    kind: str,
    resolution: str,
    from_str: str = "",
    to_str: str = "",
) -> Response:
    directory = str(_dataset_dir(dataset_id))
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        cli.cmd_series(directory, sensor_id, kind, resolution, from_str, to_str)
    return Response(content=buffer.getvalue(), media_type="application/json")


@app.get("/v1/datasets/{dataset_id}/export/{sensor_id}")
def export_sensor(
    dataset_id: str,
    sensor_id: str,
    kind: str,
    file_format: str = "csv",
) -> Response:
    directory = str(_dataset_dir(dataset_id))
    try:
        payload = export_payload(directory, sensor_id, kind, file_format)
    except ExportError as error:
        if error.code == 1:
            raise HTTPException(status_code=404, detail=str(error)) from error
        raise HTTPException(status_code=400, detail=str(error)) from error
    media = (
        "application/json; charset=utf-8"
        if file_format == "json"
        else "text/csv; charset=utf-8"
    )
    return Response(content=payload, media_type=media)
