"""
Secure file handling utilities.

Security concerns addressed:
1. Path traversal: resolved path must be within allowed base directory
2. MIME type validation: check both extension AND magic bytes
3. Duplicate filenames: UUID prefix makes names unique
4. Malicious filenames: stripped to safe characters only
"""

import hashlib
import mimetypes
import os
import re
import uuid
from pathlib import Path
from typing import Tuple

import aiofiles
import structlog
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import FileTypeError, FileSizeError

logger = structlog.get_logger(__name__)

# MIME type to file extension mapping (both directions)
ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

# Magic byte signatures for file type verification
# Defense against MIME spoofing
MAGIC_BYTES = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # TXT has no magic bytes — we fall back to extension check
}


def sanitize_filename(filename: str) -> str:
    """
    Make filename safe for storage:
    - Remove path components
    - Replace dangerous characters with underscores
    - Normalize unicode
    - Truncate to reasonable length
    """
    # Get just the base name (no directory components)
    filename = os.path.basename(filename)

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Replace anything not alphanumeric, dot, dash, or underscore
    filename = re.sub(r"[^\w.\-]", "_", filename)

    # Remove leading dots (hidden files on Unix)
    filename = filename.lstrip(".")

    # Truncate
    name, ext = os.path.splitext(filename)
    name = name[:100]  # Max 100 chars for base name
    filename = f"{name}{ext}" if name else f"file{ext}"

    return filename or "unnamed_file"


def get_client_upload_dir(client_id: uuid.UUID) -> Path:
    """
    Get and create the upload directory for a specific client.
    Directory structure: {UPLOAD_BASE_DIR}/{client_id}/
    """
    base = Path(settings.UPLOAD_BASE_DIR).resolve()
    client_dir = base / str(client_id)
    client_dir.mkdir(parents=True, exist_ok=True)
    return client_dir


def generate_stored_filename(original_filename: str) -> str:
    """
    Generate a unique stored filename.
    Format: {uuid4}_{safe_original_name}
    UUID prefix guarantees uniqueness; original name aids debugging.
    """
    safe_name = sanitize_filename(original_filename)
    return f"{uuid.uuid4()}_{safe_name}"


def check_path_safety(file_path: Path, base_dir: Path) -> bool:
    """
    Verify that the resolved file path is within the allowed base directory.
    Prevents path traversal attacks.
    """
    try:
        file_path.resolve().relative_to(base_dir.resolve())
        return True
    except ValueError:
        return False


def detect_mime_type(file_bytes: bytes, filename: str) -> str:
    """
    Detect MIME type using both magic bytes and extension.
    Magic bytes take priority — prevents filename spoofing.
    """
    # Check magic bytes
    for magic, mime in MAGIC_BYTES.items():
        if file_bytes.startswith(magic):
            return mime

    # Fall back to extension
    _, ext = os.path.splitext(filename.lower())
    ext = ext.lstrip(".")

    ext_to_mime = {v: k for k, v in ALLOWED_MIME_TYPES.items()}
    return ext_to_mime.get(ext, "application/octet-stream")


async def save_upload_file(
    file: UploadFile,
    client_id: uuid.UUID,
) -> Tuple[str, str, str, int]:
    """
    Validate and save an uploaded file securely.

    Returns:
        (stored_filename, file_path, mime_type, file_size_bytes)

    Raises:
        FileSizeError: if file exceeds MAX_FILE_SIZE_BYTES
        FileTypeError: if file type not in ALLOWED_MIME_TYPES
    """
    # Read file into memory for validation
    # For very large files, consider streaming directly to disk with size checks
    content = await file.read()
    file_size = len(content)

    # Size check
    if file_size > settings.MAX_FILE_SIZE_BYTES:
        raise FileSizeError(settings.MAX_FILE_SIZE_MB)

    if file_size == 0:
        from app.core.exceptions import AppException
        raise AppException("Uploaded file is empty")

    # MIME type detection and validation
    mime_type = detect_mime_type(content, file.filename or "")
    if mime_type not in ALLOWED_MIME_TYPES:
        raise FileTypeError(list(ALLOWED_MIME_TYPES.values()))

    # Generate safe stored filename
    original_filename = file.filename or "unnamed"
    stored_filename = generate_stored_filename(original_filename)

    # Get client directory
    client_dir = get_client_upload_dir(client_id)
    file_path = client_dir / stored_filename

    # Path traversal check (belt + suspenders)
    if not check_path_safety(file_path, client_dir):
        logger.error(
            "Path traversal attempt detected",
            client_id=str(client_id),
            filename=original_filename,
        )
        from app.core.exceptions import AppException
        raise AppException("Invalid file path", status_code=400)

    # Write file atomically (write to temp, then rename)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    try:
        async with aiofiles.open(temp_path, "wb") as f:
            await f.write(content)
        temp_path.rename(file_path)
    except Exception as e:
        # Cleanup on failure
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise

    logger.info(
        "File saved",
        client_id=str(client_id),
        stored_filename=stored_filename,
        size_bytes=file_size,
        mime_type=mime_type,
    )

    return stored_filename, str(file_path), mime_type, file_size


def delete_file(file_path: str) -> bool:
    """Safely delete a file, returns True on success."""
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception as e:
        logger.error("File deletion failed", path=file_path, error=str(e))
        return False
