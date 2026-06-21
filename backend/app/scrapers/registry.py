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

# add new scrapers here as you build them

ACTIVE_SCRAPERS = [
    RBIWhatsNewScraper, SEBICircularsScraper, SECRulemakingScraper, MASNewsScraper, ASICNewsScraper, #FCAPublicationsScraper
]