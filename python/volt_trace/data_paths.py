"""Gemeinsame Pfadlogik mit der Next.js-App (VOLT_TRACE_DATA_DIR)."""

import os
import re
import tempfile
from pathlib import Path

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def get_data_root() -> Path:
    if raw := os.environ.get("VOLT_TRACE_DATA_DIR"):
        return Path(raw)
    return Path(tempfile.gettempdir()) / "volt-trace-data"


def dataset_path(dataset_id: str) -> Path:
    if not _UUID_RE.match(dataset_id):
        raise ValueError("Ungültiger Datensatz.")
    return get_data_root() / dataset_id
