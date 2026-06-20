# backend/app/scrapers/mas.py
# ─────────────────────────────────────────────────────
#  MAS (Monetary Authority of Singapore) Scraper
#  Multi-source via discovered Solr JSON API
#
#  Data source: MAS SearchSG Solr backend (returns clean JSON)
#    https://www.mas.gov.sg/api/v1/search
#    - No Cloudflare, no auth token, no React rendering
#    - The website's own frontend calls this endpoint
#
#  Sources (each filtered by mas_mastercontenttypes_sm facet):
#    1. News        → media releases, speeches, enforcement, letters
#    2. Publications → consultations, monographs, guidelines
#
#  Why two sources:
#    News carries enforcement + policy announcements.
#    Publications carries the consultation papers and guidelines
#    that are the actual regulatory changes firms must track.
#    Either failing alone still yields partial coverage.
#
#  Solr JSON fields used:
#    document_title_string_s   → title
#    page_url_s                → relative URL
#    mas_date_tdt              → ISO8601 publish timestamp
#    mas_contenttype_s         → fine-grained type label
#    document_shortsummary_t   → summary (array, take [0])
#    numFound                  → total hits (for logging)
#
#  jurisdiction=SG, industry=fintech
# ─────────────────────────────────────────────────────

import logging
from datetime import date, datetime, timezone

import httpx

from app.scrapers.base import BaseScraper, ScrapeResult, ScrapeError

logger = logging.getLogger(__name__)

BASE = "https://www.mas.gov.sg"
SOLR_ENDPOINT = f"{BASE}/api/v1/search"

# Each source: (label, mas_mastercontenttypes_sm facet value)
SOURCES = [
    ("News", "News"),
    ("Publications", "Publications"),
]

ROWS_PER_SOURCE = 15        # newest N items per source
MIN_DOCS_EXPECTED = 3       # warn if fewer than this

MAS_HEADERS = {
    # MAS WAF returns a "Maintenance" HTML decoy to non-browser User-Agents.
    # A standard browser UA is required to receive the real Solr JSON.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

FETCH_TIMEOUT = 30.0


class MASNewsScraper(BaseScraper):
    """
    Multi-source MAS scraper hitting the Solr JSON API directly.

    Independent per-source fallback: if News fails but Publications
    succeeds (or vice versa), the cycle still produces a snapshot.
    Only a total failure of both sources returns ScrapeError.
    """

    source_url       = SOLR_ENDPOINT
    source_authority = "Monetary Authority of Singapore"
    jurisdiction     = "SG"
    industry         = "fintech"
    topic            = "financial regulation"

    # ── Override scrape() for multi-source JSON ───────

    def scrape(self) -> ScrapeResult | ScrapeError:
        scraped_at = datetime.now(timezone.utc)

        sections = []
        errors = []
        seen_urls = set()

        for label, facet_value in SOURCES:
            try:
                section = self._fetch_source(label, facet_value, seen_urls)
                if section:
                    sections.append(section)
                    logger.info("MASNewsScraper: %s ✓", label)
                else:
                    errors.append(f"{label} returned empty")
                    logger.warning("MASNewsScraper: %s returned empty", label)
            except Exception as e:
                errors.append(f"{label} failed: {e}")
                logger.warning("MASNewsScraper: %s failed — %s", label, e)

        # ── All sources failed ────────────────────────

        if not sections:
            summary = "; ".join(errors)
            logger.error("MASNewsScraper: All sources failed — %s", summary)
            return ScrapeError(
                source_url=self.source_url,
                error=f"All sources failed: {summary}",
                scraped_at=scraped_at,
            )

        # ── Partial failure: log, continue ────────────

        if errors:
            logger.warning(
                "MASNewsScraper: %d/%d sources OK, failures: %s",
                len(sections), len(SOURCES), "; ".join(errors),
            )

        # ── Merge into snapshot ───────────────────────

        separator = "=" * 60
        header = (
            "MAS Regulatory Monitor — Multi-Source Snapshot\n"
            f"Sources active: {len(sections)}/{len(SOURCES)} | "
            f"Scraped: {scraped_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"{separator}\n"
        )
        plain_text = header + "\n\n".join(sections)

        if not plain_text.strip():
            return ScrapeError(
                source_url=self.source_url,
                error="All sources returned empty content",
                scraped_at=scraped_at,
            )

        return ScrapeResult(
            source_authority=self.source_authority,
            source_url=self.source_url,
            jurisdiction=self.jurisdiction,
            industry=self.industry,
            topic=self.topic,
            content_hash=self._hash(plain_text),
            plain_text=plain_text,
            effective_date=self.get_effective_date(plain_text),
            scraped_at=scraped_at,
        )

    # ── ABC compliance (unused — scrape overridden) ───

    def parse(self, html: str) -> str:
        """Not called — scrape() fully overridden for JSON API."""
        return ""

    # ── Per-source Solr fetch ─────────────────────────

    def _fetch_source(self, label: str, facet_value: str, seen_urls: set) -> str:
        params = {
            "json.nl": "map",
            "indent": "on",
            "q": "*:*",
            "rows": str(ROWS_PER_SOURCE),
            "start": "0",
            "fq": f'mas_mastercontenttypes_sm:"{facet_value}"',
            "sort": "mas_date_tdt desc",
        }

        resp = httpx.get(
            SOLR_ENDPOINT,
            params=params,
            headers=MAS_HEADERS,
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()

        # MAS WAF returns an HTML "Maintenance" decoy (still HTTP 200) when it
        # doesn't like the request. Detect that before attempting JSON parse.
        ctype = resp.headers.get("content-type", "")
        if "json" not in ctype.lower():
            snippet = resp.text[:80].replace("\n", " ")
            raise RuntimeError(
                f"{label}: expected JSON, got {ctype or 'unknown'} "
                f"(WAF decoy?) — starts: {snippet!r}"
            )

        data = resp.json()

        response_block = data.get("response", {})
        docs = response_block.get("docs", [])
        num_found = response_block.get("numFound", 0)

        if not docs:
            logger.warning(
                "MASNewsScraper: %s returned 0 docs (numFound=%s)",
                label, num_found,
            )
            return ""

        if len(docs) < MIN_DOCS_EXPECTED:
            logger.warning(
                "MASNewsScraper: %s only %d docs (expected ≥%d)",
                label, len(docs), MIN_DOCS_EXPECTED,
            )

        lines = []
        for doc in docs:
            title = (
                doc.get("document_title_string_s")
                or doc.get("navigation_title_string_s")
                or ""
            ).strip()

            rel_url = doc.get("page_url_s", "").strip()
            url = f"{BASE}{rel_url}" if rel_url.startswith("/") else rel_url

            content_type = doc.get("mas_contenttype_s", "").strip()

            # date: "2026-06-17T18:01:20Z" → "2026-06-17"
            raw_date = doc.get("mas_date_tdt", "")
            pub_date = raw_date[:10] if raw_date else ""

            # Consultation-specific fields (Publications only)
            consult_num = ""
            num_arr = doc.get("masconsultation_consultationnumber_t", [])
            if isinstance(num_arr, list) and num_arr:
                consult_num = num_arr[0].strip()

            closing_date = ""
            raw_closing = doc.get("masconsultation_closingdate_tdt", "")
            if raw_closing:
                closing_date = raw_closing[:10]

            # summary is an array
            summary_arr = doc.get("document_shortsummary_t", [])
            summary = ""
            if isinstance(summary_arr, list) and summary_arr:
                summary = summary_arr[0].strip()
            elif isinstance(summary_arr, str):
                summary = summary_arr.strip()
            # collapse whitespace/newlines, truncate
            summary = " ".join(summary.split())
            if len(summary) > 250:
                summary = summary[:247] + "..."

            if not title:
                continue

            # dedup across sources
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            line = f"{pub_date} | {content_type} | {title}"
            if consult_num:
                line += f" [{consult_num}]"
            if url:
                line += f"\n  → {url}"
            if closing_date:
                line += f"\n  Consultation closes: {closing_date}"
            if summary:
                line += f"\n  {summary}"
            lines.append(line)

        if not lines:
            logger.warning("MASNewsScraper: %s parsed 0 usable items", label)
            return ""

        logger.info(
            "MASNewsScraper: Parsed %d items from %s (of %s total)",
            len(lines), label, num_found,
        )

        section_sep = "-" * 50
        return (
            f"[{label.upper()} — MAS Solr API]\n"
            f"Format: DATE | TYPE | TITLE\n"
            f"{section_sep}\n"
            + "\n".join(lines)
        )

    # ── Date extraction ───────────────────────────────

    def get_effective_date(self, text: str) -> date | None:
        """Newest item's date — first YYYY-MM-DD in the snapshot."""
        import re
        match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
        if match:
            try:
                return datetime.strptime(match.group(), "%Y-%m-%d").date()
            except ValueError:
                pass
        return None