# ─────────────────────────────────────────────────
#  Celery Scraper Tasks
#
#  Two tasks:
#
#  1. run_all_scrapers()
#     Triggered by Celery Beat every 15 minutes.
#     Iterates ACTIVE_SCRAPERS and dispatches
#     one run_single_scraper task per scraper.
#     Uses a Redis lock per scraper to prevent
#     overlapping runs.
#
#  2. run_single_scraper(scraper_class_name)
#     Runs one scraper, compares hash, stores
#     change if content changed.
# ─────────────────────────────────────────────────

import logging
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.change import Change
from app.scrapers.base import ScrapeError, ScrapeResult
from app.scrapers.registry import ACTIVE_SCRAPERS
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Redis lock timeout — if a scraper runs longer than this
# something is wrong, release the lock
LOCK_TIMEOUT_SECONDS = 300

@celery_app.task(name="scraper.run_all")
def run_all_scrapers():
    """
    Dispatches one task per active scraper.
    Called by Celery Beat every 15 minutes.

    Each scraper runs as a separate task so one
    slow/failing scraper doesn't block the others.
    """
    logger.info(f"Dispatching {len(ACTIVE_SCRAPERS)} scraper tasks")
    
    for scraper_class in ACTIVE_SCRAPERS:
        run_single_scraper.delay(scraper_class.__name__)
    logger.info("All scraper tasks dispatched")
    
@celery_app.task(
    name="scraper.run_single",
    max_retries=3,
    default_retry_delay=60,  # retry after 1 minute if it fails
)
def run_single_scraper(scraper_class_name: str):
    """
    Run a single scraper by class name.

    Flow:
        1. Acquire Redis lock (prevents overlapping runs)
        2. Instantiate and run the scraper
        3. Compare content hash with last stored hash
        4. If changed → store Change record with status="raw"
        5. Release lock

    The Redis lock key is: scraper_lock:<scraper_class_name>
    """
    
    redis_client = celery_app.backend.client
    lock_key = f"scraper_lock:{scraper_class_name}"
    
    # ── 1. Acquire lock ───────────────────────────
    # nx=True means only set if not exists (atomic)
    # ex= sets expiry so lock auto-releases on crash
    lock_acquired = redis_client.set(
        lock_key,
        '1',
        nx=True,
        ex=LOCK_TIMEOUT_SECONDS,
    )
    
    if not lock_acquired:
        logger.info(f"Scraper {scraper_class_name} already running — skipping")
        return
    
    try:
        # ── 2. Find and instantiate scraper ───────
        scraper_class = next(
            (s for s in ACTIVE_SCRAPERS if s.__name__ == scraper_class_name),
            None,
        )
        
        if not scraper_class:
            logger.error(f"Scraper class not found: {scraper_class_name}")
            return
        
        scraper = scraper_class()
        logger.info(f"Running scraper: {scraper_class_name} → {scraper.source_url}")
        
        # ── 3. Run scraper and get content hash ──
        result = scraper.scrape()
        
        if isinstance(result, ScrapeError):
            logger.error(
                f"Scraper {scraper_class_name} failed: {result.error}"
            )
            return
        
        _process_scrape_result(result)
        
    finally:
        # ── 5. Always release lock ────────────────
        redis_client.delete(lock_key)
        
def _process_scrape_result(result: ScrapeResult) -> None:
    """
    Compare the scrape result hash against the last
    stored hash for this source. If different — store
    a new Change record with status="raw".

    Uses a fresh DB session — not shared with request threads.
    """
    db: Session = SessionLocal()
    
    try:
        # Find the most recent change for this source
        last_change = (
            db.query(Change)
            .filter(Change.source_url == result.source_url)
            .order_by(Change.detected_at.desc())
            .first()
        )
        
        # If hash is the same — nothing changed, skip
        if last_change and last_change.content_hash == result.content_hash:
            logger.debug(
                f"No change detected for {result.source_url} "
                f"(hash: {result.content_hash[:16]}...)"
            )
            return
        
        change = Change(
            jurisdiction=result.jurisdiction,
            industry=result.industry,
            topic=result.topic,
            source_authority=result.source_authority,
            source_url=result.source_url,
            source_snapshot=result.plain_text[:10000],  # cap at 10KB
            content_hash=result.content_hash,
            archived_at=result.scraped_at,
            effective_date=result.effective_date,
            status="raw",                   # AI processing picks this up next
            processing_attempts=0,
        )
        
        db.add(change)
        db.commit()
        
        logger.info(
            f"Change stored: {change.id} "
            f"jurisdiction={result.jurisdiction} "
            f"industry={result.industry}"
        )
        
        # TODO: Trigger AI processing task here (Phase 1 Step 4)
        # process_change_with_ai.delay(change.id)

    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to store change: {e}")
        raise

    finally:
        db.close()