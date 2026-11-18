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
    d = get_settings().data_dir / "documents"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{sha256}.pdf"
    if not path.exists():
        path.write_bytes(data)
    return path
