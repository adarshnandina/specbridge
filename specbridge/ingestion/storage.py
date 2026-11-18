from __future__ import annotations

import hashlib
import re
from pathlib import Path

from specbridge.config import get_settings
from specbridge.errors import UploadError


def sanitize_filename(name: str) -> str:
    base = Path(name.replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "upload.pdf"
    return base[:120]


def validate_pdf_bytes(data: bytes, max_mb: int | None = None) -> str:
    """Check magic bytes and size; return sha256."""
    limit = (max_mb or get_settings().max_upload_mb) * 1024 * 1024
    if len(data) > limit:
        raise UploadError(f"File exceeds the {limit // (1024 * 1024)} MB upload limit")
    if not data.startswith(b"%PDF"):
        raise UploadError("File is not a PDF (missing %PDF header)")
    return hashlib.sha256(data).hexdigest()


def store_pdf(data: bytes, sha256: str) -> Path:
    """Write the PDF under DATA_DIR/documents/<sha>.pdf if missing; returns the absolute path."""
    path = get_settings().data_dir / relative_path(sha256)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)
    return path


def relative_path(sha256: str) -> str:
    return f"documents/{sha256}.pdf"


def resolve_path(storage_path: str, sha256: str) -> Path:
    """Locate a stored PDF. Paths are stored relative to DATA_DIR; legacy absolute paths still work,
    and if the recorded location is gone (data dir moved, other host) fall back to DATA_DIR."""
    data_dir = get_settings().data_dir
    candidates = (
        [Path(storage_path)] if Path(storage_path).is_absolute() else [data_dir / storage_path]
    )
    candidates.append(data_dir / relative_path(sha256))
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]
