import hashlib
from pathlib import Path

from app.core.config import settings


class DocumentStorageService:
    """Handles secure local filesystem storage for uploaded document versions."""

    @staticmethod
    def get_storage_path(organization_id: str, version_id: str) -> Path:
        """Resolve the safe filesystem destination for a document version."""
        org_dir = settings.DOCUMENT_STORAGE_PATH / organization_id
        return org_dir / f"{version_id}.dat"

    @classmethod
    def save_file(
        cls,
        organization_id: str,
        version_id: str,
        content: bytes,
    ) -> tuple[str, str, int]:
        """Save file bytes to disk using a safe server-side storage name.

        Returns (storage_path_str, sha256_hash, file_size_bytes).
        """
        dest_path = cls.get_storage_path(organization_id, version_id)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        sha256 = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        # Write to temporary file first then atomically replace to avoid partial writes
        temp_path = dest_path.with_suffix(".tmp")
        try:
            with open(temp_path, "wb") as f:
                f.write(content)
            temp_path.replace(dest_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

        return str(dest_path.resolve()), sha256, file_size

    @staticmethod
    def delete_file(storage_path_str: str) -> bool:
        """Safely delete stored file if present (e.g. on transaction rollback)."""
        try:
            p = Path(storage_path_str)
            if p.exists() and p.is_file():
                p.unlink()
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def read_file(storage_path_str: str) -> bytes:
        """Read bytes of a stored document version."""
        p = Path(storage_path_str)
        return p.read_bytes()
