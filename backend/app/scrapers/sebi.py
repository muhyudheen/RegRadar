# ─────────────────────────────────────────────────
#  SEBI Circulars Scraper
#
#  Source: Securities and Exchange Board of India
#  URL:    https://www.sebi.gov.in/sebiweb/home/HomeAction.do
#          ?doListing=yes&sid=1&ssid=7&smid=0
#
#  Page structure (server-rendered, no Playwright needed):
#    table#sample_1 > tbody > tr.odd
#      td[0] → date string e.g. "Jun 16, 2026"
#      td[1] → <a class="points" href="..." title="...">title</a>
#
#  Scraping strategy:
#    - Fetch page 1 only (latest 25 circulars)
#    - Build a text snapshot: one line per circular
#      "DATE | TITLE | URL"
#    - AI compares snapshots to detect new circulars
#    - Only page 1 needed — new circulars always appear here first
#
#  Change detection:
#    ContentHash of the snapshot string detects any new
#    circular added to the top of the list.
# ─────────────────────────────────────────────────

import logging
from bs4 import BeautifulSoup
 
from app.scrapers.base import BaseScraper
 
logger = logging.getLogger(__name__)
 
# Minimum number of circular rows we expect
# If we get fewer, the page structure may have changed
MIN_EXPECTED_ROWS = 5


class SEBICircularsScraper(BaseScraper):
    """
    Scrapes SEBI's circulars listing page (page 1 only).
 
    Monitors for new regulatory circulars from SEBI across
    all departments — covers KYC norms, mutual fund rules,
    broker regulations, FPI guidelines, and more.
    """
    
    source_url = (
        "https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
        "?doListing=yes&sid=1&ssid=7&smid=0"
    )
    source_authority = "Securities and Exchange Board of India"
    jurisdiction     = "IN"
    industry         = "fintech"
    topics           = ["securities", "kyc", "mutual-funds", "brokers"]
    
    def parse(self, html: str) -> str:
        """
        Extract circular listings from SEBI's table.
 
        Returns a text snapshot of the first page of circulars —
        one line per circular in format:
          "DATE | TITLE | URL"
 
        This snapshot is what gets stored as source_snapshot
        and sent to AI for change analysis.
        """
        soup = BeautifulSoup(html, "lxml")
        
        # Primary selector: table#sample_1
        table = soup.find("table", {"id": "sample_1"})
        
        # Fallback: any striped table on the page
        if not table:
            table = soup.find("table", class_="table-striped")
            
        if not table:
            logger.warning(
                "SEBICircularsScraper: Could not find circulars table — "
                "page structure may have changed"
            )
            # Fall back to full page text so we don't silently miss changes
            return soup.get_text(separator="\n", strip=True)[:8000]
        
        tbody = table.find("tbody")
        if not tbody:
            logger.warning("SEBICircularsScraper: No tbody in table")
            return soup.get_text(separator="\n", strip=True)[:8000]
 
        rows = tbody.find_all("tr")
        
        if len(rows) < MIN_EXPECTED_ROWS:
            logger.warning(
                f"SEBICircularsScraper: Only {len(rows)} rows found "
                f"(expected ≥{MIN_EXPECTED_ROWS}) — "
                "possible page structure change or empty response"
            )
 
        lines = []
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
 
            # td[0] = date
            date = cells[0].get_text(strip=True)
 
            # td[1] = <a class="points"> with title and href
            link = cells[1].find("a", class_="points")
            if not link:
                # Fallback: any link in the cell
                link = cells[1].find("a")
 
            if not link:
                continue
 
            title = link.get_text(strip=True)
            url   = link.get("href", "").strip()
 
            # Skip empty rows
            if not title:
                continue
 
            # Normalize relative URLs
            if url and not url.startswith("http"):
                url = f"https://www.sebi.gov.in{url}"
 
            lines.append(f"{date} | {title} | {url}")
 
        if not lines:
            logger.warning(
                "SEBICircularsScraper: Parsed 0 circulars from table — "
                "falling back to raw text"
            )
            return soup.get_text(separator="\n", strip=True)[:8000]
 
        logger.info(
            f"SEBICircularsScraper: Parsed {len(lines)} circulars"
        )
 
        # Header line for AI context
        snapshot = (
            "SEBI Circulars — Latest 25 (page 1 of listing)\n"
            "Format: DATE | TITLE | URL\n"
            "─────────────────────────────────────────────\n"
        )
        snapshot += "\n".join(lines)
 
        return snapshot