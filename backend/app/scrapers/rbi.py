# backend/app/scrapers/rbi.py
# ─────────────────────────────────────────────────
#  Reserve Bank of India — "What's New" Scraper
#
#  Source: https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx
#  Monitors: Latest circulars, guidelines, press releases
#  Jurisdiction: IN
#  Industry: fintech
#  Topic: general (covers KYC, AML, payments, etc.)
#
#  The RBI "What's New" page lists all recent publications.
#  We scrape the listing page — if anything is added,
#  the hash changes and we record it as a change.
# ─────────────────────────────────────────────────

import re
from datetime import datetime, timezone, date

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper

class RBIWhatsNewScraper(BaseScraper):
    
    source_url = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
    source_authority = "Reserve Bank of India"
    jurisdiction = "IN"
    industry = "fintech"
    topic = "general"
    
    def parse(self, html: str) -> str:
        try:
            soup = BeautifulSoup(html, "lxml")
            content_parts = []

            # Try multiple selectors — RBI changes their HTML structure
            selectors = [
                ("table", {"class": "tablebg"}),
                ("table", {"class": "table"}),
                ("div", {"id": "mainContent"}),
                ("div", {"class": "content"}),
                ("main", {}),
            ]

            for tag, attrs in selectors:
                elements = soup.find_all(tag, attrs) if attrs else soup.find_all(tag)
                if elements:
                    for el in elements[:3]:
                        text = el.get_text(separator=" ", strip=True)
                        if len(text) > 100:    # only meaningful content
                            content_parts.append(text)
                    if content_parts:
                        break

            # Last fallback — body text
            if not content_parts:
                body = soup.find("body")
                if body:
                    content_parts.append(body.get_text(separator=" ", strip=True))

            return " ".join(content_parts) if content_parts else html

        except Exception as e:
            return html
    def get_effective_date(self, text: str) -> date | None:
        """
        Try to extract the most recent date mentioned in the content.
        RBI typically uses formats like: "June 04, 2026" or "04/06/2026"
        """
        pattern = r"(January|February|March|April|May|June|July|August|" \
                  r"September|October|November|December)\s+\d{1,2},\s+\d{4}"
        match = re.search(pattern, text)
        if match:
            try:
                return datetime.strptime(match.group(), "%B %d, %Y").date()
            except ValueError:
                pass
        return None
        