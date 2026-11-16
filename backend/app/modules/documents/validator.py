import io
import zipfile
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import (
    InvalidRequestException,
    PayloadTooLargeException,
    UnsupportedMediaTypeException,
)

CANONICAL_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def sanitize_filename(filename: str | None) -> str:
    """Extract safe basename from uploaded filename and prevent path traversal."""
    if not filename or not filename.strip():
        raise InvalidRequestException("Filename cannot be empty")

    # Strip path components from Windows and POSIX separators
    raw_name = Path(filename).name
    # Remove control characters and illegal filesystem characters
    clean_name = "".join(
        c for c in raw_name if c.isprintable() and c not in '\\/:*?"<>|'
    ).strip()

    if not clean_name:
        raise InvalidRequestException("Invalid filename")

    return clean_name


def validate_file_extension(filename: str) -> str:
    """Validate that file extension is supported and return normalized extension."""
    clean_name = sanitize_filename(filename)
    suffix = Path(clean_name).suffix.lower()

    if suffix not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        raise UnsupportedMediaTypeException(
            f"Unsupported file extension '{suffix}'. Allowed formats: {allowed}"
        )

    return suffix


def validate_file_content(content: bytes, extension: str) -> str:
    """Validate file content, size, and magic-byte signature.

    Returns the canonical MIME type if valid; raises an exception otherwise.
    """
    if len(content) == 0:
        raise InvalidRequestException("Uploaded file is empty (0 bytes)")

    if len(content) > settings.MAX_FILE_SIZE_BYTES:
        max_mb = settings.MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise PayloadTooLargeException(
            f"File exceeds maximum allowed size of {max_mb:.1f} MB"
        )

    canonical_mime = CANONICAL_MIME_TYPES.get(extension)
    if not canonical_mime:
        raise UnsupportedMediaTypeException(f"Unsupported extension '{extension}'")

    if extension == ".pdf":
        # PDF files must start with the %PDF- magic bytes
        if not content.startswith(b"%PDF-"):
            raise UnsupportedMediaTypeException(
                "Invalid PDF file: Missing %PDF- signature"
            )

    elif extension == ".docx":
        # DOCX files are ZIP packages starting with PK\x03\x04
        if not content.startswith(b"PK\x03\x04"):
            raise UnsupportedMediaTypeException(
                "Invalid DOCX file: Missing PK ZIP signature"
            )
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = zf.namelist()
                if "[Content_Types].xml" not in namelist:
                    raise UnsupportedMediaTypeException(
                        "Invalid DOCX package: Missing [Content_Types].xml"
                    )
        except zipfile.BadZipFile as e:
            raise UnsupportedMediaTypeException(
                "Invalid DOCX package: Corrupted ZIP archive"
            ) from e

    elif extension == ".txt":
        # TXT files must not contain null bytes (which indicate raw binary files)
        if b"\x00" in content:
            raise UnsupportedMediaTypeException(
                "Invalid TXT file: Binary null byte detected"
            )
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise UnsupportedMediaTypeException(
                "Invalid TXT file: Content is not valid UTF-8 text"
            ) from e

    return canonical_mime
