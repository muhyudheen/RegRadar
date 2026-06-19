# backend/app/scrapers/sec.py
# ─────────────────────────────────────────────────────
#  SEC Rulemaking Scraper (multi-source with fallback)
#
#  Sources (all .gov — no Cloudflare, no bot blocking):
#    1. Rulemaking Activity page (HTML table)
#       https://www.sec.gov/rules-regulations/rulemaking-activity
#       → proposed rules, final rules, concept releases
#
#    2. Press Releases RSS feed (XML)
#       https://www.sec.gov/news/pressreleases.rss
#       → rule announcements, enforcement, policy changes
#
#    3. Speeches & Statements RSS feed (XML)
#       https://www.sec.gov/news/speeches-statements.rss
#       → commissioner statements, policy direction signals
#
#  Fallback logic:
#    - Each source fetched independently with its own try/except
#    - If ALL three fail → return ScrapeError
#    - If SOME fail → log warning, continue with what succeeded
#    - If ALL succeed → merge all into one snapshot
#    - Deduplicate by URL across sources
#
#  SEC bot policy:
#    - Requires descriptive User-Agent with contact email
#    - Max 10 req/sec (we do 3 requests per 15 min — well within)
#    - https://www.sec.gov/about/developer-resources
#
#  Change detection:
#    Combined snapshot is hashed. Any new rule, press release,
#    or statement changes the hash → triggers AI analysis.
# ─────────────────────────────────────────────────────

import logging
from datetime import date, datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScrapeResult, ScrapeError

logger = logging.getLogger(__name__)

# ── Source URLs ──────────────────────────────────────

RULEMAKING_URL = "https://www.sec.gov/rules-regulations/rulemaking-activity"
PRESS_RSS_URL = "https://www.sec.gov/news/pressreleases.rss"
STATEMENTS_RSS_URL = "https://www.sec.gov/news/speeches-statements.rss"

# ── Thresholds ───────────────────────────────────────

MIN_RULEMAKING_ROWS = 3
MIN_RSS_ITEMS = 3
MAX_RSS_ITEMS = 15       # cap each RSS source to keep snapshot manageable
MAX_RULEMAKING_ROWS = 20 # recent rules only, not full history

# ── SEC requires descriptive UA with contact ─────────

SEC_HEADERS = {
    "User-Agent": "Lawhook/1.0 (regulatory monitoring; contact@lawhook.dev)",
    "Accept": "text/html, application/rss+xml, application/xml, text/xml",
}

FETCH_TIMEOUT = 30.0


class SECRulemakingScraper(BaseScraper):
    """
    Multi-source SEC scraper with independent fallback per source.

    Monitors US federal securities regulation across three SEC feeds.
    Any single source dying does not kill the scraper — the others
    continue and partial snapshots still detect changes.

    jurisdiction=US, industry=fintech — subscribers filtering on
    US securities regulation receive these changes.
    """

    source_url       = RULEMAKING_URL  # primary, shown in logs/DB
    source_authority = "U.S. Securities and Exchange Commission"
    jurisdiction     = "US"
    industry         = "fintech"
    topic            = "securities"

    # ── Override scrape() for multi-source ────────────

    def scrape(self) -> ScrapeResult | ScrapeError:
        """
        Fetch from 3 SEC sources independently, merge into one snapshot.
        Never raises — all errors caught and returned.
        """
        scraped_at = datetime.now(timezone.utc)

        sections = []       # successful source snapshots
        errors = []         # failed source descriptions
        seen_urls = set()   # dedup across sources

        # ── Source 1: Rulemaking Activity (HTML table) ──

        try:
            rulemaking_text = self._fetch_rulemaking_activity(seen_urls)
            if rulemaking_text:
                sections.append(rulemaking_text)
                logger.info("SECRulemakingScraper: Rulemaking activity ✓")
            else:
                errors.append("Rulemaking activity returned empty")
                logger.warning("SECRulemakingScraper: Rulemaking activity returned empty")
        except Exception as e:
            errors.append(f"Rulemaking activity failed: {e}")
            logger.warning("SECRulemakingScraper: Rulemaking activity failed — %s", e)

        # ── Source 2: Press Releases RSS ─────────────────

        try:
            press_text = self._fetch_rss(
                PRESS_RSS_URL, "Press Releases", seen_urls
            )
            if press_text:
                sections.append(press_text)
                logger.info("SECRulemakingScraper: Press releases RSS ✓")
            else:
                errors.append("Press releases RSS returned empty")
                logger.warning("SECRulemakingScraper: Press releases RSS returned empty")
        except Exception as e:
            errors.append(f"Press releases RSS failed: {e}")
            logger.warning("SECRulemakingScraper: Press releases RSS failed — %s", e)

        # ── Source 3: Speeches & Statements RSS ──────────

        try:
            statements_text = self._fetch_rss(
                STATEMENTS_RSS_URL, "Speeches & Statements", seen_urls
            )
            if statements_text:
                sections.append(statements_text)
                logger.info("SECRulemakingScraper: Speeches & statements RSS ✓")
            else:
                errors.append("Speeches & statements RSS returned empty")
                logger.warning("SECRulemakingScraper: Speeches/statements RSS returned empty")
        except Exception as e:
            errors.append(f"Speeches/statements RSS failed: {e}")
            logger.warning("SECRulemakingScraper: Speeches/statements RSS failed — %s", e)

        # ── All failed? ──────────────────────────────────

        if not sections:
            error_summary = "; ".join(errors)
            logger.error(
                "SECRulemakingScraper: All 3 sources failed — %s", error_summary
            )
            return ScrapeError(
                source_url=self.source_url,
                error=f"All sources failed: {error_summary}",
                scraped_at=scraped_at,
            )

        # ── Partial failure? Log but continue ────────────

        if errors:
            logger.warning(
                "SECRulemakingScraper: %d/3 sources succeeded, %d failed: %s",
                len(sections), len(errors), "; ".join(errors),
            )

        # ── Merge into final snapshot ────────────────────

        separator = "=" * 60
        header = (
            "SEC Regulatory Monitor — Multi-Source Snapshot\n"
            f"Sources active: {len(sections)}/3 | "
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

    # ── ABC compliance (not used — scrape() is overridden) ──

    def parse(self, html: str) -> str:
        """Not called — scrape() is fully overridden for multi-source."""
        return ""

    # ── Source 1: Rulemaking Activity (HTML) ──────────

    def _fetch_rulemaking_activity(self, seen_urls: set) -> str:
        """
        Fetch and parse the rulemaking activity HTML table.

        Table structure (Drupal-rendered):
          <table> rows with: Issue Date | File Number | Rulemaking | Status
          Status column contains <a> links to proposed/final rule pages
        """
        resp = httpx.get(
            RULEMAKING_URL,
            headers=SEC_HEADERS,
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Primary: find the rulemaking table
        table = soup.select_one("table")

        if not table:
            logger.warning(
                "SECRulemakingScraper: No table found on rulemaking page — "
                "SEC may have redesigned"
            )
            # Fallback: grab page text
            fallback = soup.get_text(separator="\n", strip=True)[:6000]
            return f"[RULEMAKING — FALLBACK: raw page text]\n{fallback}" if fallback else ""

        rows = table.select("tbody tr") or table.select("tr")

        if len(rows) < MIN_RULEMAKING_ROWS:
            logger.warning(
                "SECRulemakingScraper: Only %d rulemaking rows (expected ≥%d)",
                len(rows), MIN_RULEMAKING_ROWS,
            )

        lines = []
        for row in rows[:MAX_RULEMAKING_ROWS]:
            cells = row.select("td")
            if len(cells) < 3:
                continue

            issue_date = cells[0].get_text(strip=True)
            file_number = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            rulemaking = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            status = cells[3].get_text(strip=True) if len(cells) > 3 else ""

            # Get detail URL from status column link
            status_link = cells[3].find("a") if len(cells) > 3 else None
            url = ""
            if status_link:
                url = status_link.get("href", "").strip()
                if url and not url.startswith("http"):
                    url = f"https://www.sec.gov{url}"

            if not rulemaking:
                continue

            # Dedup
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)

            line = f"{issue_date} | {file_number} | {rulemaking}"
            if status:
                line += f" | {status}"
            if url:
                line += f"\n  → {url}"
            lines.append(line)

        if not lines:
            logger.warning("SECRulemakingScraper: Parsed 0 rulemaking entries")
            return ""

        logger.info(
            "SECRulemakingScraper: Parsed %d rulemaking entries", len(lines)
        )

        section_sep = "-" * 50
        return (
            "[RULEMAKING ACTIVITY — Proposed & Final Rules]\n"
            "Format: DATE | FILE# | TITLE | STATUS\n"
            f"{section_sep}\n"
            + "\n".join(lines)
        )

    # ── Source 2 & 3: RSS feeds ──────────────────────

    def _fetch_rss(self, url: str, label: str, seen_urls: set) -> str:
        """
        Fetch and parse an SEC RSS feed (XML).

        Works for both press releases and speeches/statements feeds.
        Uses BeautifulSoup for XML parsing (no feedparser dependency).
        """
        resp = httpx.get(
            url,
            headers=SEC_HEADERS,
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()

        # RSS is XML — use lxml-xml parser
        # Fallback to lxml (HTML mode) if xml parser not available
        try:
            soup = BeautifulSoup(resp.text, "lxml-xml")
        except Exception:
            soup = BeautifulSoup(resp.text, "lxml")

        items = soup.find_all("item")

        if not items:
            # Some RSS feeds use <entry> (Atom format)
            items = soup.find_all("entry")

        if len(items) < MIN_RSS_ITEMS:
            logger.warning(
                "SECRulemakingScraper: Only %d items in %s RSS (expected ≥%d)",
                len(items), label, MIN_RSS_ITEMS,
            )

        lines = []
        for item in items[:MAX_RSS_ITEMS]:
            title = ""
            link = ""
            pub_date = ""
            description = ""

            # <title>
            title_el = item.find("title")
            if title_el:
                title = title_el.get_text(strip=True)

            # <link> (RSS) or <link href="..."> (Atom)
            link_el = item.find("link")
            if link_el:
                link = link_el.get_text(strip=True) or link_el.get("href", "").strip()

            # <pubDate> (RSS) or <published> (Atom)
            date_el = item.find("pubDate") or item.find("published")
            if date_el:
                pub_date = date_el.get_text(strip=True)

            # <description> (RSS) or <summary> (Atom)
            desc_el = item.find("description") or item.find("summary")
            if desc_el:
                # Strip HTML from description
                raw_desc = desc_el.get_text(strip=True)
                description = BeautifulSoup(raw_desc, "lxml").get_text(strip=True)
                # Truncate long descriptions
                if len(description) > 200:
                    description = description[:197] + "..."

            if not title:
                continue

            # Dedup across sources
            if link and link in seen_urls:
                continue
            if link:
                seen_urls.add(link)

            line = f"{pub_date} | {title}"
            if link:
                line += f" | {link}"
            if description:
                line += f"\n  → {description}"
            lines.append(line)

        if not lines:
            logger.warning(
                "SECRulemakingScraper: Parsed 0 items from %s RSS", label
            )
            return ""

        logger.info(
            "SECRulemakingScraper: Parsed %d items from %s RSS",
            len(lines), label,
        )

        section_sep = "-" * 50
        return (
            f"[{label.upper()} — RSS Feed]\n"
            f"Format: DATE | TITLE | URL\n"
            f"{section_sep}\n"
            + "\n".join(lines)
        )

    # ── Date extraction override ─────────────────────

    def get_effective_date(self, text: str) -> date | None:
        """
        Try to extract the most recent date from the snapshot.
        The first rulemaking entry's date is the best signal.
        """
        import re

        # Match patterns like "June 11, 2026" or "May 29, 2026"
        match = re.search(
            r"(January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{1,2},\s+\d{4}",
            text,
        )
        if match:
            try:
                return datetime.strptime(match.group(), "%B %d, %Y").date()
            except ValueError:
                pass
        return None