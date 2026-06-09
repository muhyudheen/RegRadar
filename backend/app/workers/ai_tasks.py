# ─────────────────────────────────────────────────
#  AI Processing Celery Task
#
#  Triggered by scraper_tasks.py after a raw change
#  is stored in the DB.
#
#  Flow:
#    1. Load Change record from DB (status="raw")
#    2. Mark as "processing" — prevents double processing
#    3. Find previous snapshot for diff context
#    4. Call Claude API via ai_processor.py
#    5. Store summary, severity, diff back on Change
#    6. Mark as "ready" → webhook delivery picks it up
#    7. On failure → mark as "failed", increment attempts
#       Retry up to 3 times with exponential backoff
# ─────────────────────────────────────────────────

import logging
from datetime import datetime, timezone

from app.core.ai_processor import AIError, AIResult, process_change
from app.core.database import SessionLocal
from app.models.change import Change
from app.workers.celery_app import celery_app
from celery.exceptions import Retry

logger = logging.getLogger(__name__)

MAX_PROCESSING_ATTEMPTS = 3

@celery_app.task(
    name="ai.process_change",
    bind=True,
    max_retries=MAX_PROCESSING_ATTEMPTS,
    default_retry_delay=60,  # retry after 1 minute if it fails
)
def process_change_with_ai(self, change_id: str):
    """
    Process a raw regulatory change with Claude AI.
 
    Args:
        change_id: The Change.id to process
 
    Transitions:
        raw → processing → ready    (success)
        raw → processing → failed   (all retries exhausted)
    """
    db = SessionLocal()
    
    try:
        # 1. Load Change record
        change = db.query(Change).filter(Change.id == change_id).first()
        
        if not change:
            logger.error(f"Change with id {change_id} not found")
            return
        
        if change.status != "raw":
            logger.info(
                f"Change {change_id} status is '{change.status}' — skipping"
            )
            return
 
        # 2. Mark as processing
        # prevents another worker picking up the same change
        change.status = "processing"
        change.processing_attempts += 1
        db.commit()
        
        logger.info(
            f"Processing change {change_id} "
            f"(attempt {change.processing_attempts}/{MAX_PROCESSING_ATTEMPTS})"
        )
        
        # 3. Find previous snapshot for diff context
        # Get the second-most-recent change for this source
        # so Claude can compare old vs new
        previous_change = (
            db.query(Change)
            .filter(
                Change.source_url == change.source_url,
                Change.id != change.id,
            )
            .order_by(Change.detected_at.desc())
            .first()
        )
        
        old_text = previous_change.source_snapshot if previous_change else None
        
        # 4. Call Claude API via ai_processor.py
        result = process_change(
            source_authority=change.source_authority,
            jurisdiction=change.jurisdiction,
            industry=change.industry,
            topic=change.topic,
            old_text=old_text,
            new_text=change.source_snapshot or "",
        )
        
        # 5. Store summary, severity, diff back on Change
        if isinstance(result, AIError):
            _handle_ai_failure(self, change, db, result.error)
            return
        
        if isinstance(result, AIResult):
            _handle_ai_success(change, db, result)
            return
    
    
    except Retry:
        # This exception is raised by self.retry() to trigger a retry.
        # We can just let it propagate to Celery.
        raise    
    except Exception as e:
        logger.exception(f"Unexpected error processing change {change_id}: {e}")
        if db:
            try:
                change = db.query(Change).filter(Change.id == change_id).first()
                if change:
                    _handle_ai_failure(self, change, db, str(e))
            except Exception:
                db.rollback()
        raise
 
    finally:
        db.close()
        
def _handle_ai_success(
    change: Change,
    db,
    result: AIResult,
) -> None:
    """Store AI results and mark change as ready for webhook delivery."""
    change.summary      = result.summary
    change.severity     = result.severity
    change.diff         = result.diff
    change.status       = "ready"
    change.processed_at = datetime.now(timezone.utc)
    change.processing_error = None
    db.commit()
    
    logger.info(
        f"Change {change.id} processed successfully — "
        f"severity={result.severity} status=ready"
    )
    
    # Trigger webhook delivery for this change
    # Import here to avoid circular imports
    from app.workers.webhook_tasks import deliver_change_webhooks
    deliver_change_webhooks.delay(change.id)
    
def _handle_ai_failure(
    task,
    change: Change,
    db,
    error: str,
) -> None:
    """
    Handle AI processing failure.
    Retries up to MAX_PROCESSING_ATTEMPTS times.
    After all retries exhausted — marks as failed.
    """
    if change.processing_attempts < MAX_PROCESSING_ATTEMPTS:
        # More retries available — put back to raw for retry
        change.status = "raw"
        db.commit()
 
        logger.warning(
            f"Change {change.id} AI processing failed "
            f"(attempt {change.processing_attempts}/{MAX_PROCESSING_ATTEMPTS}): "
            f"{error} — retrying"
        )
 
        # Exponential backoff: 60s, 120s, 240s
        countdown = 60 * (2 ** (change.processing_attempts - 1))
        raise task.retry(
            exc=Exception(error),
            countdown=countdown,
        )
    else:
        # All retries exhausted
        change.status = "failed"
        db.commit()
 
        logger.error(
            f"Change {change.id} AI processing permanently failed "
            f"after {change.processing_attempts} attempts: {error}"
        )
 
    