"""
FCAPublicationsScraper — queries FCA's Funnelback search JSON API directly.
Bypasses fca.org.uk Cloudflare Bot Management entirely.
"""
import logging
from datetime import datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

FUNNELBACK_URL = "https://fcauk-search.funnelback.squiz.cloud/s/search.json"
FUNNELBACK_PARAMS = {
    "collection": "fcauk~sp-push-prod",
    "profile": "_default",
    "query": "!showall",
    "sort": "dmetaZ",
    "num_ranks": "10",
    "start_rank": "1",
}
# Passed as repeated params — httpx handles list values correctly
FUNNELBACK_TYPES = [
    "consultation papers",
    "finalised guidance",
    "policy statements",
    "regulatory priorities",
]


class FCAPublicationsScraper(BaseScraper):
    source_name = "FCA"
    jurisdiction = "GB"
    source_url = FUNNELBACK_URL  # used in logs / DB; not fetched directly

    def scrape(self) -> list[dict[str, Any]]:
        """Override scrape() fully — we speak JSON, not HTML."""
        try:
            params = list(FUNNELBACK_PARAMS.items())
            for t in FUNNELBACK_TYPES:
                params.append(("f.Type|fbType", t))

            resp = httpx.get(
                FUNNELBACK_URL,
                params=params,
                timeout=30,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; Lawhook/1.0)",
                },
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "FCAPublicationsScraper: HTTP %s from Funnelback",
                exc.response.status_code,
            )
            return []
        except Exception as exc:
            logger.error("FCAPublicationsScraper: Request failed — %s", exc)
            return []

        results = (
            data.get("response", {})
                .get("resultPacket", {})
                .get("results", [])
        )
        if not results:
            logger.warning(
                "FCAPublicationsScraper: Empty results from Funnelback — "
                "collection/profile may have changed"
            )
            return []

        publications = []
        for r in results:
            title = r.get("title", "").strip()
            url = r.get("liveUrl", "").strip()
            summary = r.get("summary", "").strip()

            # Funnelback date: "2026-06-15T00:00:00" or epoch string
            raw_date = r.get("date", "") or r.get("indexDate", "")
            pub_date = _parse_date(raw_date)

            # Category lives in metaData under various keys
            meta = r.get("metaData", {})
            category = (
                meta.get("c", "")      # fbType
                or meta.get("e", "")   # category
                or ""
            ).strip()

            if not title or not url:
                continue

            publications.append({
                "title": title,
                "url": url,
                "summary": summary,
                "published_date": pub_date,
                "category": category,
                "jurisdiction": self.jurisdiction,
                "source": self.source_name,
            })

        logger.info(
            "FCAPublicationsScraper: Parsed %d publications", len(publications)
        )
        return publications

    def parse(self, html: str) -> list:
        """Not used — scrape() is fully overridden to use JSON API."""
        return []

def _parse_date(raw: str) -> str | None:
    """Best-effort ISO date string from Funnelback date field."""
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw[:19], fmt).date().isoformat()
        except ValueError:
            continue
    return None