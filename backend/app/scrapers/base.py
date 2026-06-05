# ─────────────────────────────────────────────────
#  Abstract Base Scraper
#
#  Every scraper inherits from BaseScraper and
#  implements the fetch() method.
#
#  BaseScraper handles:
#  - HTTP fetching with timeout + size cap
#  - Redirect limiting (max 3 redirects)
#  - Content hashing
#  - HTML → plain text stripping (prevents XSS in DB)
#  - Error handling and logging
#
#  Security guarantees:
#  - Max response size: 5MB (OOM protection)
#  - Max redirects: 3 (open redirect protection)
#  - Timeout: 30s connect, 60s read
#  - No user-controlled URLs (hardcoded in subclasses)
# ─────────────────────────────────────────────────

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from datetime import date, datetime, timezone

import httpx
from bs4 import BeautifulSoup 

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5MB
MAX_REDIRECTS = 3
CONNECT_TIMEOUT = 30.0
READ_TIMEOUT = 60.0

JS_RENDER_THRESHOLD = 600 # Playwright

@dataclass
class ScrapeResult:
    source_authority: str
    source_url: str
    jurisdiction:     str
    industry:         str
    topic:            str | None
    content_hash:     str
    plain_text:       str
    effective_date:   date | None
    scraped_at:       datetime
    
@dataclass
class ScrapeError:
    source_url: str
    error:      str
    scraped_at: datetime
    
class BaseScraper(ABC):
    """
    Abstract base class for all project scrapers.
 
    Subclasses must define:
        source_url, source_authority, jurisdiction, industry
 
    Subclasses must implement:
        parse(html: str) -> str
 
    Subclasses may override:
        get_effective_date(text: str) -> date | None
    """
    source_url:       str
    source_authority: str
    jurisdiction:     str
    industry:         str
    topic:            str | None = None
    
    _httpx_client: httpx.Client | None = None
    
    # ----------------public entry------------
    
    def scrape(self) -> ScrapeResult | ScrapeError:
        """
        Fetch, parse, hash. Returns ScrapeResult or ScrapeError.
        Never raises — all errors caught and returned.
        """
        scraped_at = datetime.now(timezone.utc)
        
        try:
            html = self._fetch(self.source_url)
            relevant = self.parse(html)
            plain_text = self.strip_to_plain_text(relevant)
            
            if not plain_text.strip():
                return ScrapeError(
                    source_url=self.source_url,
                    error="Parse returned empty content",
                    scraped_at=scraped_at,
                )
                
            return ScrapeResult(
                source_authority = self.source_authority,
                source_url       = self.source_url,
                jurisdiction     = self.jurisdiction,
                industry         = self.industry,
                topic            = self.topic,
                content_hash     = self._hash(plain_text),
                plain_text       = plain_text,
                effective_date   = self.get_effective_date(plain_text),
                scraped_at       = scraped_at,
            )
            
        except httpx.TimeoutException as e:
            return ScrapeError(self.source_url, f"Timeout: {e}", scraped_at)
        except httpx.TooManyRedirects as e:
            return ScrapeError(self.source_url, f"Too many redirects (max {MAX_REDIRECTS})", scraped_at)
        except httpx.HTTPError as e:
            return ScrapeError(self.source_url, f"HTTP error: {e}", scraped_at)
        except Exception as e:
            logger.exception(f"Unexpected scrape error for {self.source_url}")
            return ScrapeError(self.source_url, f"{type(e).__name__}: {e}", scraped_at)
        
    # ----------------Abstract methods------------
    
    @abstractmethod
    def parse(self, html: str) -> str:
        """Extract the relevant section from the page HTML"""
        raise NotImplementedError
    
    def get_effective_date(self, text: str) -> date | None:
        """Override in subclasses for source-specific date parsing."""
        return None
    
    # ── Fetch strategy: httpx → Playwright ───────

    def _fetch(self, url: str) -> str:
        """
        Fetch strategy:
          1. Try httpx (fast, no browser)
          2. If content looks JS-rendered (sparse body) → Playwright
          3. If httpx errors → Playwright
        """
        
        try:
            html = self._fetch_httpx(url)
            
            body_text = BeautifulSoup(html, 'lxml').get_text(strip=True)
            if len(body_text) < JS_RENDER_THRESHOLD:
                logger.info(
                    f"{url} returned {len(body_text)} chars via httpx "
                    f"(threshold {JS_RENDER_THRESHOLD}) — trying Playwright"
                )
                return self._fetch_playwright(url)
 
            return html
        
        except Exception as e:
            logger.warning(f"HTTP fetch failed for {url}: {e} - trying playwright")
            return self._fetch_playwright(url)
        
    def _fetch_httpx(self, url: str) -> str:
        """
        Fetch via httpx with streaming size cap.
        Fast path — used for server-rendered pages.
        """
        client = self._get_httpx_client()

        with client.stream("GET", url) as response:
            response.raise_for_status()
 
            chunks      = []
            total_bytes = 0
            
            for chunk in response.iter_bytes(chunk_size=8192):
                total_bytes += len(chunk)
                if total_bytes > MAX_RESPONSE_BYTES:
                    logger.warning(f"{url} exceeded {MAX_RESPONSE_BYTES}B — truncating")
                    chunks.append(
                        chunk[:MAX_RESPONSE_BYTES - (total_bytes - len(chunk))]
                    )
                    break
                chunks.append(chunk)
                
            raw = b"".join(chunks)
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1", errors="replace")
            
    def _fetch_playwright(self, url: str) -> str:
        """
        Fetch via headless Chromium.
        Slow path — used for JS-rendered government sites.
        Waits for network idle so dynamic content is loaded.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. "
                "Run: playwright install chromium"
            )
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_extra_http_headers({
                    "User-Agent": "RegRadar-Scraper/1.0 (compliance monitoring)" #change it to the upcoming original name
                })
                
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                html = page.content()
                
# Playwright has no built-in size cap — apply one manually
                if len(html.encode("utf-8")) > MAX_RESPONSE_BYTES:
                    logger.warning(f"Playwright response for {url} exceeds cap — truncating")
                    html = html[:MAX_RESPONSE_BYTES]
 
                return html
 
            finally:
                browser.close()
                
    @classmethod
    @classmethod
    def _get_httpx_client(cls) -> httpx.Client:
        if cls._httpx_client is None:
            cls._httpx_client = httpx.Client(
                timeout=httpx.Timeout(
                    connect=CONNECT_TIMEOUT,
                    read=READ_TIMEOUT,
                    write=10.0,
                    pool=5.0,
                ),
                follow_redirects=True,
                max_redirects=MAX_REDIRECTS,
                headers={"User-Agent": "RegRadar-Scraper/1.0 (compliance monitoring)"}, # change it to the upcoming original name
            )
        return cls._httpx_client
    
    # ── Utility methods ───────
    
    @staticmethod
    def _strip_to_plain_text(html: str) -> str:
        """
        Strip HTML to plain text.
        Security: raw HTML is never stored — prevents XSS
        if content is rendered in the dashboard or API.
        """
        try:
            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return re.sub(r"\s+", " ", text).strip()
        except Exception as e:
            logger.warning(f"HTML stripping failed: {e} — using regex fallback")
            return re.sub(r"<[^>]+>", " ", html).strip()
 
    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()