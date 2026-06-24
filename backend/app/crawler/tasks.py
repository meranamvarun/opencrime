"""Celery tasks for the FIR crawler.

Task hierarchy:
  crawl_all_states()
    └─► crawl_state_task(state_code)          [one per state, fanout]
          └─► crawl_district_task(code, dist)  [one per district, parallel]

Each district task:
  1. Instantiates the spider with a rotating proxy
  2. Iterates over FIRDocument objects
  3. Deduplicates against Redis
  4. Saves the file to UPLOAD_DIR
  5. Creates a Document DB record
  6. Queues the existing process_document Celery task (OCR → AI → store)
"""
from __future__ import annotations

import logging
import os
import uuid

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "crawler",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

_CRAWL_DIR = os.path.join(settings.UPLOAD_DIR, "crawled")
os.makedirs(_CRAWL_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------

@celery_app.task(name="crawler.crawl_all_states")
def crawl_all_states() -> dict:
    """Fan out a crawl task for every registered state."""
    from app.crawler.registry import SPIDER_REGISTRY

    dispatched = 0
    for state_code in SPIDER_REGISTRY:
        crawl_state_task.delay(state_code)
        dispatched += 1
    logger.info("Weekly crawl dispatched for %d states", dispatched)
    return {"states_dispatched": dispatched}


@celery_app.task(name="crawler.crawl_state_task", bind=True, max_retries=2)
def crawl_state_task(self, state_code: str) -> dict:
    """Fan out per-district tasks for one state."""
    from app.crawler.registry import SPIDER_REGISTRY

    cls = SPIDER_REGISTRY.get(state_code)
    if not cls:
        logger.warning("No spider registered for %s", state_code)
        return {"error": "unknown state"}

    dispatched = 0
    for district in cls.districts:
        crawl_district_task.delay(state_code, district)
        dispatched += 1

    logger.info("%s: dispatched %d district tasks", state_code, dispatched)
    return {"state": state_code, "districts_dispatched": dispatched}


# ---------------------------------------------------------------------------
# Per-district worker
# ---------------------------------------------------------------------------

@celery_app.task(
    name="crawler.crawl_district_task",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def crawl_district_task(self, state_code: str, district: str) -> dict:
    """Run one spider for a single district and feed results into the pipeline."""
    from app.crawler.registry import SPIDER_REGISTRY
    from app.crawler.dedupe import FIRDeduplicator
    from app.crawler.proxy import get_pool
    from app.core.database import SessionLocal
    from app.models.crime_record import Document, ProcessingStatus

    cls = SPIDER_REGISTRY.get(state_code)
    if not cls:
        return {"error": "unknown state"}

    deduper = FIRDeduplicator()
    proxy = get_pool().get_proxy()
    spider = cls(proxy_url=proxy)
    db = SessionLocal()

    saved = skipped = errors = 0

    try:
        for fir_doc in spider.crawl_district(district):
            fp = deduper.fingerprint(fir_doc.fingerprint_key)
            if deduper.seen(fp):
                skipped += 1
                continue

            try:
                file_path = _persist(fir_doc)
                doc = Document(
                    filename=os.path.basename(file_path),
                    original_filename=f"{fir_doc.fir_number}.{fir_doc.file_ext}",
                    file_path=file_path,
                    file_type=fir_doc.file_ext,
                    file_size=len(fir_doc.content),
                    status=ProcessingStatus.PENDING,
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)

                # Hand off to the existing OCR+AI pipeline
                from app.workers.processing import process_document
                process_document.delay(str(doc.id))

                deduper.mark_seen(fp)
                saved += 1
            except Exception as exc:
                errors += 1
                logger.warning("%s/%s: failed to save FIR %s: %s",
                               state_code, district, fir_doc.fir_number, exc)

    except Exception as exc:
        logger.error("%s/%s: spider crashed: %s", state_code, district, exc)
        raise self.retry(exc=exc)
    finally:
        spider.close()
        db.close()

    logger.info("%s/%s: saved=%d skipped=%d errors=%d",
                state_code, district, saved, skipped, errors)
    return {"state": state_code, "district": district,
            "saved": saved, "skipped": skipped, "errors": errors}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _persist(fir_doc) -> str:
    """Write FIR bytes to UPLOAD_DIR and return the absolute path."""
    fname = f"{fir_doc.state_code}_{fir_doc.district}_{fir_doc.fir_number}_{fir_doc.year}_{uuid.uuid4().hex[:8]}.{fir_doc.file_ext}"
    # Sanitise: replace spaces and slashes
    fname = fname.replace(" ", "_").replace("/", "-")
    path = os.path.join(_CRAWL_DIR, fname)
    with open(path, "wb") as f:
        f.write(fir_doc.content)
    return path
