import logging
import os
import signal
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from types import FrameType

from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.database.session import SessionLocal
from app.models.document import DocumentVersion
from app.modules.ingestion.extractors.factory import ExtractorFactory
from app.modules.ingestion.job_queue import JobQueueService
from app.modules.ingestion.schemas import DocumentExtractionError

logger = logging.getLogger("knowledgeops.ingestion.worker")

TRANSIENT_ERROR_CODES = {
    "DATABASE_LOCKED",
    "STORAGE_FILE_READ_ERROR",
    "TRANSIENT_IO_ERROR",
    "UNEXPECTED_ERROR",
}


class IngestionWorker:
    """Background worker that claims and processes document ingestion jobs."""

    def __init__(
        self,
        worker_id: str | None = None,
        poll_interval: float | None = None,
        lease_seconds: int | None = None,
        base_backoff_seconds: int | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self.worker_id = worker_id or f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self.poll_interval = poll_interval or settings.WORKER_POLL_INTERVAL_SECONDS
        self.lease_seconds = lease_seconds or settings.WORKER_LEASE_SECONDS
        self.base_backoff_seconds = (
            base_backoff_seconds or settings.WORKER_BASE_BACKOFF_SECONDS
        )
        self.session_factory = session_factory or SessionLocal
        self.running = False

    def process_one_job(self) -> bool:
        """Attempt to claim and process a single pending or expired job.

        Returns True if a job was found and processed; False if queue was empty.
        """
        # Step 1: Claim job under a short DB transaction
        claim_db = self.session_factory()
        try:
            job = JobQueueService.claim_next_job(
                db=claim_db,
                worker_id=self.worker_id,
                lease_duration_seconds=self.lease_seconds,
            )
            if not job:
                return False

            job_id = job.id
            version_id = job.document_version_id
            version = claim_db.get(DocumentVersion, version_id)
            if not version:
                logger.error(
                    f"Claimed job {job_id} references missing version {version_id}"
                )
                JobQueueService.fail_job(
                    db=claim_db,
                    job_id=job_id,
                    error_code="VERSION_NOT_FOUND",
                    error_message=f"Version {version_id} not found in database",
                    is_retryable=False,
                )
                return True

            storage_path_str = version.storage_path
            mime_type = version.mime_type
            original_filename = version.original_filename
        finally:
            claim_db.close()

        logger.info(
            f"Worker {self.worker_id} claimed {job_id} for '{original_filename}'"
        )

        # Step 2: Extract content outside any active database transaction
        storage_path = Path(storage_path_str)
        try:
            extractor = ExtractorFactory.get_extractor(
                mime_type=mime_type,
                filename=original_filename,
            )
            extracted_doc = extractor.extract(storage_path)
        except DocumentExtractionError as e:
            is_retryable = e.code in TRANSIENT_ERROR_CODES
            fail_db = self.session_factory()
            try:
                JobQueueService.fail_job(
                    db=fail_db,
                    job_id=job_id,
                    error_code=e.code,
                    error_message=e.message,
                    is_retryable=is_retryable,
                    base_backoff_seconds=self.base_backoff_seconds,
                )
            finally:
                fail_db.close()
            return True
        except Exception as e:
            logger.exception(f"Unexpected error extracting job {job_id}: {e}")
            fail_db = self.session_factory()
            try:
                JobQueueService.fail_job(
                    db=fail_db,
                    job_id=job_id,
                    error_code="UNEXPECTED_ERROR",
                    error_message=str(e),
                    is_retryable=True,
                    base_backoff_seconds=self.base_backoff_seconds,
                )
            finally:
                fail_db.close()
            return True

        # Step 3: Persist extracted pages and complete job in a short DB transaction
        complete_db = self.session_factory()
        try:
            JobQueueService.complete_job(
                db=complete_db,
                job_id=job_id,
                extracted_doc=extracted_doc,
            )
        except Exception as e:
            logger.exception(f"Database error completing job {job_id}: {e}")
            fail_db = self.session_factory()
            try:
                JobQueueService.fail_job(
                    db=fail_db,
                    job_id=job_id,
                    error_code="DATABASE_LOCKED",
                    error_message=f"Failed to persist extracted pages: {e}",
                    is_retryable=True,
                    base_backoff_seconds=self.base_backoff_seconds,
                )
            finally:
                fail_db.close()
        finally:
            complete_db.close()

        return True

    def run(self) -> None:
        """Start worker loop with signal handling for graceful shutdown."""
        self.running = True

        def handle_shutdown(signum: int, frame: FrameType | None) -> None:
            sig_name = signal.Signals(signum).name
            logger.info(f"Worker {self.worker_id} got {sig_name}; shutting down...")
            self.running = False

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        logger.info(
            f"Worker {self.worker_id} started (poll={self.poll_interval}s, "
            f"lease={self.lease_seconds}s)"
        )

        while self.running:
            try:
                did_work = self.process_one_job()
                if not did_work and self.running:
                    time.sleep(self.poll_interval)
            except Exception as e:
                logger.exception(f"Error in worker main loop: {e}")
                if self.running:
                    time.sleep(self.poll_interval)

        logger.info(f"Ingestion worker {self.worker_id} stopped.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    worker = IngestionWorker()
    worker.run()
