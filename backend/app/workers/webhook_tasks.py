# backend/app/workers/webhook_tasks.py
# ─────────────────────────────────────────────────
#  Webhook Delivery Tasks
#
#  Triggered by ai_tasks.py after a change is "ready".
#
#  Flow:
#    1. Load the Change from DB
#    2. Find all active subscriptions that match:
#       - same jurisdiction
#       - same industry
#       - severity_min threshold met
#    3. Create one WebhookDelivery record per subscription
#    4. Fire each webhook via webhook.py (SSRF-safe, signed)
#    5. Update delivery status + retry if failed
#
#  Retry schedule (from webhook.py):
#    Attempt 1 fails → 60s
#    Attempt 2 fails → 5 min
#    Attempt 3 fails → 30 min
#    Attempt 4 fails → 2 hrs
#    Attempt 5 fails → 24 hrs
#    After 5         → permanently failed
# ─────────────────────────────────────────────────

import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.change import Change
from app.models.subscription import Subscription
from app.models.webhook_delivery import WebhookDelivery
from app.workers.celery_app import celery_app
from app.workers.webhook import deliver_webhook, next_retry_at

logger = logging.getLogger(__name__)

# Severity ordering — used to check severity_min threshold
SEVERITY_RANK = {
    "minor":    1,
    "major":    2,
    "critical": 3,
}


@celery_app.task(name="webhook.deliver_change")
def deliver_change_webhooks(change_id: str) -> None:
    """
    Find all matching subscriptions for a change and
    create + fire one webhook delivery per subscription.

    Called once per change after AI processing completes.
    Each delivery is then handled independently so one
    failing endpoint doesn't block the others.
    """
    db = SessionLocal()

    try:
        # ── 1. Load change ────────────────────────
        change = db.query(Change).filter(Change.id == change_id).first()

        if not change:
            logger.error(f"Change {change_id} not found")
            return

        if change.status != "ready":
            logger.warning(
                f"Change {change_id} status is '{change.status}' "
                f"— expected 'ready', skipping"
            )
            return

        # ── 2. Find matching subscriptions ────────
        matching = _find_matching_subscriptions(db, change)

        if not matching:
            logger.info(
                f"Change {change_id}: no matching subscriptions "
                f"for {change.jurisdiction}/{change.industry} "
                f"severity={change.severity}"
            )
            return

        logger.info(
            f"Change {change_id}: found {len(matching)} matching "
            f"subscription(s) — queuing deliveries"
        )

        # ── 3. Create delivery records + fire ─────
        for subscription in matching:
            delivery_id = str(uuid.uuid4())

            # Build payload
            payload = _build_payload(change, delivery_id)

            # Create delivery record
            delivery = WebhookDelivery(
                id=delivery_id,
                change_id=change.id,
                subscription_id=subscription.id,
                webhook_url=subscription.webhook_url,
                status="pending",
                attempt_count=0,
                max_attempts=5,
                payload_snapshot=json.dumps(payload),
            )
            db.add(delivery)
            db.commit()

            # Fire the delivery as a separate task
            # Each delivery is independent — one failure
            # doesn't block others
            fire_webhook_delivery.delay(delivery_id)

    except Exception as e:
        logger.exception(f"Error in deliver_change_webhooks: {e}")
        db.rollback()
        raise

    finally:
        db.close()


@celery_app.task(
    name="webhook.fire_delivery",
    bind=True,
    max_retries=5,
)
def fire_webhook_delivery(self, delivery_id: str) -> None:
    """
    Fire a single webhook delivery attempt.

    Uses the SafeIPTransport from webhook.py for:
    - DNS rebinding protection (re-resolves at delivery time)
    - TLS SNI fix (connects to verified IP, keeps domain for SNI)
    - Redirect blocking (follow_redirects=False)
    - HMAC-SHA256 signing with per-subscription secret
    """
    db = SessionLocal()

    try:
        # ── Load delivery + subscription ──────────
        delivery = db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()

        if not delivery:
            logger.error(f"Delivery {delivery_id} not found")
            return

        if delivery.status == "success":
            logger.info(f"Delivery {delivery_id} already succeeded — skipping")
            return

        subscription = db.query(Subscription).filter(
            Subscription.id == delivery.subscription_id
        ).first()

        if not subscription:
            logger.error(
                f"Subscription {delivery.subscription_id} not found "
                f"for delivery {delivery_id}"
            )
            delivery.status = "failed"
            delivery.last_error = "Subscription not found"
            db.commit()
            return

        # ── Update attempt tracking ───────────────
        delivery.attempt_count += 1
        delivery.last_attempted_at = datetime.now(timezone.utc)
        if delivery.attempt_count == 1:
            delivery.first_attempted_at = datetime.now(timezone.utc)
        db.commit()

        # ── Load payload ──────────────────────────
        payload = json.loads(delivery.payload_snapshot)

        # ── Fire webhook (via webhook.py) ─────────
        result = deliver_webhook(
            webhook_url=delivery.webhook_url,
            payload=payload,
            signing_secret=subscription.signing_secret,
            attempt_number=delivery.attempt_count,
        )

        # ── Handle result ─────────────────────────
        delivery.last_http_status  = result.get("http_status")
        delivery.last_latency_ms   = result.get("latency_ms")
        delivery.last_response_body = result.get("response_body")
        delivery.last_error        = result.get("error")

        if result["success"]:
            delivery.status       = "success"
            delivery.delivered_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"Delivery {delivery_id} succeeded "
                f"(HTTP {result.get('http_status')} "
                f"in {result.get('latency_ms')}ms)"
            )

        elif result.get("is_redirect_attack"):
            # Redirect attack — do NOT retry, mark as failed
            delivery.status = "failed"
            db.commit()
            logger.error(
                f"Delivery {delivery_id} rejected — redirect attack detected: "
                f"{result.get('error')}"
            )

        else:
            # Genuine failure — schedule retry
            retry_at = next_retry_at(delivery.attempt_count)

            if retry_at is None:
                # All retries exhausted
                delivery.status = "failed"
                db.commit()
                logger.error(
                    f"Delivery {delivery_id} permanently failed after "
                    f"{delivery.attempt_count} attempts: {result.get('error')}"
                )
            else:
                delivery.status        = "retrying"
                delivery.next_retry_at = retry_at
                db.commit()

                logger.warning(
                    f"Delivery {delivery_id} failed "
                    f"(attempt {delivery.attempt_count}): "
                    f"{result.get('error')} — retrying at {retry_at}"
                )

                # Schedule retry at the right time
                delay_seconds = (retry_at - datetime.now(timezone.utc)).seconds
                raise self.retry(
                    exc=Exception(result.get("error")),
                    countdown=delay_seconds,
                )

    except Exception as e:
        if not isinstance(e, self.MaxRetriesExceededError):
            logger.exception(f"Unexpected error in fire_webhook_delivery: {e}")
        db.rollback()
        raise

    finally:
        db.close()


# ── Helpers ───────────────────────────────────────

def _find_matching_subscriptions(
    db,
    change: Change,
) -> list[Subscription]:
    """
    Find all active subscriptions that match this change.

    Matching rules:
    - jurisdiction must match exactly
    - industry must match exactly
    - is_active must be True
    - severity_min threshold must be met:
        minor    → deliver all severities
        major    → deliver major + critical only
        critical → deliver critical only
    """
    # Get all active subscriptions for this jurisdiction + industry
    candidates = db.query(Subscription).filter(
        Subscription.jurisdiction == change.jurisdiction,
        Subscription.industry     == change.industry,
        Subscription.is_active    == True,
    ).all()

    change_rank = SEVERITY_RANK.get(change.severity or "minor", 1)

    # Filter by severity threshold
    matching = [
        sub for sub in candidates
        if SEVERITY_RANK.get(sub.severity_min, 1) <= change_rank
    ]

    return matching


def _build_payload(change: Change, delivery_id: str) -> dict:
    """
    Build the webhook payload for a change.
    This is what the developer's server receives.
    """
    return {
        "event":      "regulation.changed",
        "delivery_id": delivery_id,
        "change_id":  change.id,
        "jurisdiction": change.jurisdiction,
        "industry":   change.industry,
        "topic":      change.topic,
        "severity":   change.severity,
        "summary":    change.summary,
        "source": {
            "authority":   change.source_authority,
            "url":         change.source_url,
            "archived_at": change.archived_at.isoformat()
            if change.archived_at else None,
        },
        "diff":           change.diff,
        "effective_date": change.effective_date.isoformat()
        if change.effective_date else None,
        "detected_at":    change.detected_at.isoformat()
        if change.detected_at else None,
    }