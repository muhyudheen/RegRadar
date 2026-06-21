# ─────────────────────────────────────────────────────
#  ASIC (Australian Securities and Investments Commission)
#  Newsroom Scraper
#
#  Data source: ASIC's static newsroom JSON on their CDN
#    https://download.asic.gov.au/scripts/newsroom/newsroom-all.json
#    - One static file, ~6,800 items, the entire newsroom
#    - The asic.gov.au newsroom page is a JS SPA that downloads
#      this file and filters it client-side; we hit the file directly
#    - Served via CloudFront, no auth, no pagination, no query params
#    - Browser User-Agent required (WAF/CDN filters non-browser UAs)
#
#  Each item carries everything inline (no second lookup needed):
#    name             → title (prefixed with doc number, e.g. "26-130MR ...")
#    publishedDate    → ISO8601 timestamp
#    url              → relative path (prepend https://www.asic.gov.au)
#    documentNumber   → reference, e.g. "26-130MR"
#    metaType         → "media release" | "speech" | "news item" | "article"
#    metaSubject      → topic tags (array, may be empty)
#    metaFunction     → e.g. ["enforcement"] (array, may be empty)
#    metaDescription  → clean summary text (use this, NOT `summary`,
#                       which only holds an <img> tag)
#
#  Filtering:
#    Keep items whose metaType is a regulatory-signal type.
#    Sort by publishedDate desc, take the newest N.
#
#  jurisdiction=AU, industry=fintech
# ─────────────────────────────────────────────────────

import logging
from datetime import date, datetime, timezone
 
import httpx
 
from app.scrapers.base import BaseScraper, ScrapeResult, ScrapeError
 
logger = logging.getLogger(__name__)
 
ASIC_URL = "https://download.asic.gov.au/scripts/newsroom/newsroom-all.json"
 
ASIC_HEADERS = {
    # ASIC's CDN serves non-browser User-Agents a block/error page.
    # A standard browser UA is required to receive the JSON.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# metaType values that count as regulatory signal (lower-cased for matching)
RELEVANT_TYPES = {"media release", "speech", "news item", "article"}
 
MAX_ITEMS = 20
MIN_ITEMS_EXPECTED = 3
FETCH_TIMEOUT = 30.0
 
BASE = "https://www.asic.gov.au"


class ASICNewsScraper(BaseScraper):
    """
    Single-source ASIC scraper hitting the static newsroom JSON file.
 
    One GET to the CDN file returns the entire newsroom (~6,800 items);
    we filter to regulatory-signal types, sort newest-first, and snapshot
    the top N. No pagination or query params — the whole dataset is one file.
    """
    
    source_url = ASIC_URL
    source_authority = "Australian Securities and Investments Commission"
    jurisdiction = "AU"
    industry = "fintech"
    topic = "financial regulation"
    
    # ── Override scrape() — single JSON source ────────
    
    def scrape(self) -> ScrapeResult | ScrapeError:
        scraped_at = datetime.now(timezone.utc)
        
        # ── Fetch ─────────────────────────────────────
        try:
            resp = httpx.get(
                ASIC_URL,
                headers=ASIC_HEADERS,
                timeout=FETCH_TIMEOUT,
                follow_redirects=True,
            )
            resp.raise_for_status()
            
            # Guard against a non-JSON block/error page (still HTTP 200)
            ctype = resp.headers.get("Content-Type", "")
            if "json" not in ctype.lower():
                snippet = resp.text[:80].replace("\n", " ")
                return ScrapeError(
                    source_url=ASIC_URL,
                    error=f"Expected JSON, got {ctype or 'unknown'} — starts: {snippet!r}",
                    scraped_at=scraped_at,
                )
                
            data = resp.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "ASICNewsScraper: HTTP %s from ASIC newsroom",
                e.response.status_code,
            )
            return ScrapeError(
                source_url=ASIC_URL,
                error=f"HTTP {e.response.status_code} from ASIC newsroom",
                scraped_at=scraped_at,
            )
        except Exception as e:
            logger.error("ASICNewsScraper: Fetch failed — %s", e)
            return ScrapeError(
                source_url=ASIC_URL,
                error=f"Fetch failed: {e}",
                scraped_at=scraped_at,
            )
            
        # ── Validate shape ────────────────────────────
        if not isinstance(data, list):
            return ScrapeError(
                source_url=ASIC_URL,
                error=f"Expected a JSON list, got {type(data).__name__}",
                scraped_at=scraped_at,
            )
            
        # ── Filter to relevant types ──────────────────
        relevant = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            meta_type = entry.get("metaType", "").strip().lower()
            if meta_type in RELEVANT_TYPES:
                relevant.append(entry)
                
        if not relevant:
            logger.warning("ASICNewsScraper: No relevant items found in newsroom JSON")
            return ScrapeError(
                source_url=ASIC_URL,
                error="No relevant items found in newsroom JSON",
                scraped_at=scraped_at,
            )
            
        # ── Sort newest-first by publishedDate ────────
        # publishedDate is ISO8601 ("2026-06-19T17:45:00Z"); lexical sort on
        # that format equals chronological sort, so a plain string sort works.
        relevant.sort(
            key=lambda e: e.get("publishedDate", ""),
            reverse=True,
        )
        
        top = relevant[:MAX_ITEMS]
        
        if len(top) < MIN_ITEMS_EXPECTED:
            logger.warning(
                "ASICNewsScraper: Only %d relevant items found (expected >= %d)",
                len(top),
                MIN_ITEMS_EXPECTED,
            )
            
        # ── Build snapshot lines (one per item) ───────
        lines = []
        for entry in top:
            title = (entry.get("name") or "").strip()
            if not title:
                continue
            
            # date: "2026-06-19T17:45:00Z" → "2026-06-19"
            raw_date = entry.get("publishedDate", "")
            pub_date = raw_date[:10] if raw_date else ""
            
            rel_url = entry.get("url", "").strip()
            url = f"{BASE}{rel_url}" if rel_url.startswith("/") else rel_url
            
            meta_type = (entry.get("metaType") or "").strip()
            doc_number = (entry.get("documentNumber") or "").strip()
            
            # metaSubject / metaFunction are arrays, may be empty
            subjects = entry.get("metaSubject") or []
            functions = entry.get("metaFunction") or []
            tags = ", ".join([*subjects, *functions])
            
            # use metaDescription (real text), NOT summary (just an <img>)
            desc = (entry.get("metaDescription") or "").strip()
            desc = " ".join(desc.split())  # collapse whitespace
            if len(desc) > 250:
                desc = desc[:247] + "..."
                
            line = f"{pub_date} | {meta_type} | {title}"
            if doc_number:
                line += f" [{doc_number}]"
            if url:
                line += f"\n  → {url}"
            if tags:
                line += f"\n  Tags: {tags}"
            if desc:
                line += f"\n  {desc}"
            lines.append(line)
            
        if not lines:
            return ScrapeError(
                source_url=ASIC_URL,
                error="Relevant items found but none had usable titles",
                scraped_at=scraped_at,
            )
               
        logger.info("ASICNewsScraper: Parsed %d items", len(lines))
            
            # ── Assemble final plain-text snapshot ────────
        separator = "=" * 60
        header = (
            "ASIC Newsroom Monitor — Snapshot\n"
            f"Items: {len(lines)} | "
            f"Scraped: {scraped_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"{separator}\n"
        )
        plain_text = header + "\n\n".join(lines)
        
        # ── Return ScrapeResult ───────────────────────
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
        """Not called — scrape() is fully overridden for the JSON source."""
        return ""
 
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