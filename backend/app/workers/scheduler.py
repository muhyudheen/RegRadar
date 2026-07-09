# ─────────────────────────────────────────────────
#  Demand-Driven Scheduler 
#
#  Returns e.g. {"IN": 3600, "US": 86400, "SG": 900}
#
#  Jurisdictions with NO active demand do not appear as keys.
# ─────────────────────────────────────────────────

import logging
import time

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.rate_limiter import TIER_CADENCE_SECONDS, DEFAULT_CADENCE_SECONDS
from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.models.user import User
from app.workers.celery_app import celery_app
from app.workers.scraper_tasks import run_single_scraper
from app.scrapers.registry import all_active_jurisdictions, scrapers_for_jurisdiction

logger = logging.getLogger(__name__)

LAST_SCRAPED_KEY_PREFIX = "last_scraped:"
 
 
def _last_scraped_key(jurisdiction: str) -> str:
    return f"{LAST_SCRAPED_KEY_PREFIX}{jurisdiction}"

def get_jurisdiction_cadences() -> dict[str, int]:
    """
    Survey ALL active subscriptions and compute the fastest demanded
    cadence per jurisdiction
    """
    db: Session = SessionLocal()
    
    jurisdiction_cadences: dict[str, int] = {}
    
    try:
        rows = (
            db.query(Subscription.jurisdiction, User.tier)
            .join(APIKey, Subscription.api_key_id == APIKey.id)
            .join(User, APIKey.user_id == User.id)
            .filter(
                Subscription.is_active == True,  # noqa: E712
                APIKey.is_active == True,        # noqa: E712
                User.is_active == True,          # noqa: E712
            )
            .distinct().all()
        )
        
        for jurisdiction, tier in rows:
            cadence = TIER_CADENCE_SECONDS.get(tier, DEFAULT_CADENCE_SECONDS)
            
            current = jurisdiction_cadences.get(jurisdiction)
            if current is None or cadence < current:
                jurisdiction_cadences[jurisdiction] = cadence
                
        logger.info(
            f"Demand computed for {len(jurisdiction_cadences)} jurisdiction(s): "
            f"{jurisdiction_cadences}"
        )
        return jurisdiction_cadences

    except Exception as e:
        logger.exception(f"Failed to compute jurisdiction cadences: {e}")
        
        return {}
    
    finally:
        db.close()
    
def get_last_scraped(jurisdiction: str) -> int | None:
    """
    Unix timestamp (seconds) of the last successful scrape dispatch for
    this jurisdiction, or None if it has never been scraped.
    A corrupt/unparseable value is also treated as None
    """
    redis_client = celery_app.backend.client
    
    try:
        raw = redis_client.get(_last_scraped_key(jurisdiction))
    except Exception as e:
        logger.warning(f"Redis read failed for {jurisdiction}: {e}")
        return None
 
    if raw is None:
        return None

    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return int(raw)
    except (ValueError, AttributeError, UnicodeDecodeError):
        logger.warning(
            f"Corrupt last_scraped value for {jurisdiction}: {raw!r} — "
            f"treating as never scraped"
        )
        return None
    
def set_last_scraped(jurisdiction: str) -> None:
    """
    Mark this jurisdiction as scraped NOW.
 
    MUST only be called after a successful dispatch. If a scrape fails and
    we stamp it anyway, the jurisdiction looks "done" and will not retry for
    a full cadence — a broken scraper would silently go dark for up to 24h.
 
    No TTL: the keyspace is tiny (one key per jurisdiction, ~6 keys) and an
    expiring key would make a jurisdiction look never-scraped, resetting its
    cadence and triggering an immediate re-scrape. Persistence is correct here.
    """
    redis_client = celery_app.backend.client
    
    try:
        redis_client.set(_last_scraped_key(jurisdiction), int(time.time()))
    except Exception as e:
        logger.warning(f"Redis write failed for {jurisdiction}: {e}")
        
@celery_app.task(
    name = 'scheduler.tick',
)
def scheduler_tick() -> None:
    """
    Beat fires this every 15 min (matching the fastest cadence, enterprise).
    It surveys demand, intersects with what we can scrape, and dispatches
    only the jurisdictions whose cadence has elapsed.
    """
    
    cadences = get_jurisdiction_cadences()      # ONE query, all demand
    scrapable = all_active_jurisdictions()      # what we have scrapers for
    now = int(time.time())
    
    dispatched, skipped = 0, 0
    
    for jurisdiction, cadence in cadences.items():
        if jurisdiction not in scrapable:
            logger.info(f"{jurisdiction}: demand exists but no active scraper — skipping")
            continue
        
        last = get_last_scraped(jurisdiction)
        due = last is None or (now - last) >= cadence
        
        if not due:
            logger.debug(f"{jurisdiction}: not due (last={last}, cadence={cadence}s)")
            skipped += 1
            continue
        
        scrapers = scrapers_for_jurisdiction(jurisdiction)
        logger.info(
            f"{jurisdiction}: due (cadence={cadence}s) — dispatching {len(scrapers)} scraper(s)"
        )
        for scraper_class in scrapers:
            run_single_scraper.delay(scraper_class.__name__)
            
        set_last_scraped(jurisdiction)
        dispatched += 1
        
    logger.info(f"Tick complete: {dispatched} jurisdiction(s) dispatched, {skipped} skipped")