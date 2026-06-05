# ─────────────────────────────────────────────────
#  Scraper Registry
#
#  Central list of all active scrapers.
#  Add new scrapers here as you build them.
#  The Celery task iterates this list every 15 minutes.
# ─────────────────────────────────────────────────

from app.scrapers.rbi import RBIWhatsNewScraper

# add new scrapers here as you build them

ACTIVE_SCRAPERS = [
    RBIWhatsNewScraper(),
]