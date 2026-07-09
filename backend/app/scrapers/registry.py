# ─────────────────────────────────────────────────
#  Scraper Registry
#
#  Central list of all active scrapers.
#  Add new scrapers here as you build them.
#  The Celery task iterates this list every 15 minutes.
# ─────────────────────────────────────────────────

from app.scrapers.rbi import RBIWhatsNewScraper
from app.scrapers.sebi import SEBICircularsScraper
from app.scrapers.fca import FCAPublicationsScraper
from app.scrapers.sec import SECRulemakingScraper
from app.scrapers.mas import MASNewsScraper
from app.scrapers.asic import ASICNewsScraper
from app.scrapers.base import BaseScraper
from collections import defaultdict

# add new scrapers here as you build them

ACTIVE_SCRAPERS = [
    RBIWhatsNewScraper, SEBICircularsScraper, SECRulemakingScraper, MASNewsScraper, ASICNewsScraper, #FCAPublicationsScraper
]

JURISDICTION_SCRAPERS: dict[str, list[type[BaseScraper]]] = defaultdict(list)
for _scraper in ACTIVE_SCRAPERS:
    JURISDICTION_SCRAPERS[_scraper.jurisdiction].append(_scraper)
    
JURISDICTION_SCRAPERS = dict(JURISDICTION_SCRAPERS)  # convert back to normal dict for easier inspection

def scrapers_for_jurisdiction(jurisdiction: str) -> list[type[BaseScraper]]:
    """Scraper classes registered for one jurisdiction (empty list if none)."""
    return JURISDICTION_SCRAPERS.get(jurisdiction, [])

def all_active_jurisdictions() -> set[str]:
    """Every jurisdiction that has at least one active scraper."""
    return set(JURISDICTION_SCRAPERS.keys())
    
    
    
    