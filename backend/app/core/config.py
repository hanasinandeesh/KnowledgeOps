import os
from pathlib import Path

from dotenv import load_dotenv

_file_path = Path(__file__).resolve()
_project_root = _file_path.parent.parent.parent.parent

# Load .env from project root or backend folder
_env_root = _project_root / ".env"
_env_backend = _project_root / "backend" / ".env"
_env_path = _env_root if _env_root.exists() else _env_backend
load_dotenv(_env_path)


def _resolve_database_url(url: str) -> str:
    """Resolve relative SQLite paths to absolute paths anchored at project root."""
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        rel_path = url.replace("sqlite:///", "")
        if not Path(rel_path).is_absolute():
            abs_path = (_project_root / rel_path).resolve()
            return f"sqlite:///{abs_path.as_posix()}"
    return url


def _resolve_storage_path(path_str: str) -> Path:
    """Resolve relative storage paths to absolute paths anchored at project root."""
    p = Path(path_str)
    if not p.is_absolute():
        return (_project_root / p).resolve()
    return p.resolve()


class Settings:
    """Application settings loaded from environment variables."""

    APP_ENV: str = os.getenv("APP_ENV", "development")
    DATABASE_URL: str = _resolve_database_url(
        os.getenv(
            "DATABASE_URL",
            "sqlite:///./data/sqlite/knowledgeops.db",
        )
    )

    # JWT & Authentication Configuration (Task 003)
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "insecure-dev-secret-key-change-in-production-1234567890",
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )

    # Document Storage & Validation Configuration (Task 004)
    DOCUMENT_STORAGE_PATH: Path = _resolve_storage_path(
        os.getenv(
            "DOCUMENT_STORAGE_PATH",
            "./data/documents",
        )
    )
    MAX_FILE_SIZE_BYTES: int = int(
        os.getenv("MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024))
    )  # 10 MB default
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt"}

    # Ingestion Worker Configuration (Task 005)
    WORKER_POLL_INTERVAL_SECONDS: float = float(
        os.getenv("WORKER_POLL_INTERVAL_SECONDS", "2.0")
    )
    WORKER_LEASE_SECONDS: int = int(os.getenv("WORKER_LEASE_SECONDS", "120"))
    WORKER_MAX_ATTEMPTS: int = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))
    WORKER_BASE_BACKOFF_SECONDS: int = int(
        os.getenv("WORKER_BASE_BACKOFF_SECONDS", "5")
    )

    # Embeddings & Vector Indexing Configuration (Task 006)
    CHROMA_PERSISTENCE_PATH: Path = _resolve_storage_path(
        os.getenv("CHROMA_PERSISTENCE_PATH", "./data/chroma")
    )
    CHROMA_COLLECTION_NAME: str = os.getenv(
        "CHROMA_COLLECTION_NAME", "knowledgeops_chunks"
    )
    EMBEDDING_MODEL_ID: str = os.getenv("EMBEDDING_MODEL_ID", "BAAI/bge-small-en-v1.5")
    EMBEDDING_CACHE_DIR: Path = _resolve_storage_path(
        os.getenv("EMBEDDING_CACHE_DIR", "./data/models/embeddings")
    )
    CHUNK_TARGET_TOKENS: int = int(os.getenv("CHUNK_TARGET_TOKENS", "500"))
    CHUNK_OVERLAP_TOKENS: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "80"))
    CHUNK_MIN_TOKENS: int = int(os.getenv("CHUNK_MIN_TOKENS", "80"))
    CHUNK_MAX_TOKENS: int = int(os.getenv("CHUNK_MAX_TOKENS", "700"))


settings = Settings()
