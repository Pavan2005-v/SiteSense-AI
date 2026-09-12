"""
Bounded Polite Crawler for Brand AI-Readiness and Engagement Auditing.
Safely extracts HTML, structure, headers, links, images, and JSON-LD from targeted domains.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import re
import time
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from skills.common.models import PageData, CrawlSummary
from skills.common.page_classifier import classify_page
from skills.common.site_classifier import classify_site
from skills.common.url_utils import normalize_url
from .robots_checker import RobotsChecker


USER_AGENT = (
    "AdobeBrandReadinessAuditor/1.0 "
    "(+https://adobe.com/hackathon-2026; read-only bot)"
)

REQUEST_TIMEOUT = 6.0
MAX_PAGES_DEFAULT = 15
MAX_DEPTH_DEFAULT = 2


def calculate_url_priority(url: str) -> int:
    """Assigns priority weight to URLs to ensure high-value pages are crawled first."""
    u = url.lower()

    if u.endswith("/") or urlparse(u).path.strip("/") == "":
        return 100

    for keyword, score in [
        ("about", 90),
        ("product", 85),
        ("pricing", 85),
        ("service", 80),
        ("contact", 75),
        ("feature", 70),
        ("solution", 70),
        ("blog", 50),
        ("docs", 50),
    ]:
        if keyword in u:
            return score

    return 30


class BoundedCrawler:
    def __init__(
        self,
        base_url: str,
        max_pages: int = MAX_PAGES_DEFAULT,
        max_depth: int = MAX_DEPTH_DEFAULT,
        timeout: float = REQUEST_TIMEOUT,
        session: Optional[requests.Session] = None
    ):
        # Normalize target base URL
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            base_url = "https://" + base_url

        self.base_url = base_url.rstrip("/")
        parsed = urlparse(self.base_url)

        self.domain = parsed.netloc.lower()
        self.scheme = parsed.scheme

        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout

        self.session = session or requests.Session()

        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
        })

        self.robots_checker: Optional[RobotsChecker] = None

    def fetch_robots(self) -> Optional[RobotsChecker]:
        robots_url = f"{self.scheme}://{self.domain}/robots.txt"

        try:
            resp = self.session.get(
                robots_url,
                timeout=self.timeout
            )

            if resp.status_code == 200:
                self.robots_checker = RobotsChecker(
                    self.base_url,
                    resp.text
                )
                return self.robots_checker

        except Exception:
            pass

        self.robots_checker = RobotsChecker(
            self.base_url,
            ""
        )

        return self.robots_checker

    def fetch_llms_txt(self) -> Tuple[bool, str]:
        """
        Fetch optional /llms.txt discovery manifest.

        Returns:
            (found, content)
        """
        llms_url = f"{self.scheme}://{self.domain}/llms.txt"

        try:
            resp = self.session.get(
                llms_url,
                timeout=self.timeout
            )

            if resp.status_code == 200:
                content_type = resp.headers.get(
                    "Content-Type",
                    ""
                ).lower()

                # Accept plain-text responses.
                # Avoid treating HTML error pages as llms.txt.
                if "text/plain" in content_type or not content_type:
                    return True, resp.text

        except requests.RequestException:
            pass

        return False, ""

    def parse_page(
        self,
        url: str,
        html: str,
        status_code: int,
        depth: int,
        headers: Dict[str, str]
    ) -> PageData:

        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements for clean text extraction
        for element in soup(["script", "style", "noscript"]):
            element.extract()

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        # Title & Meta
        title = (
            soup.title.string.strip()
            if soup.title and soup.title.string
            else ""
        )

        meta_desc = ""
        meta_robots = ""
        canonical_url = None

        meta_d = soup.find(
            "meta",
            attrs={"name": re.compile(r"^description$", re.I)}
        )

        if meta_d:
            meta_desc = (
                meta_d.get("content") or ""
            ).strip()

        meta_r = soup.find(
            "meta",
            attrs={"name": re.compile(r"^robots$", re.I)}
        )

        if meta_r:
            meta_robots = (
                meta_r.get("content") or ""
            ).strip()

        canonical = soup.find(
            "link",
            rel=re.compile(r"canonical", re.I)
        )

        if canonical:
            canonical_url = (
                canonical.get("href") or ""
            ).strip()

        # Headings
        h1s = [
            h.get_text(strip=True)
            for h in soup.find_all("h1")
            if h.get_text(strip=True)
        ]

        h2s = [
            h.get_text(strip=True)
            for h in soup.find_all("h2")
            if h.get_text(strip=True)
        ]

        # Links
        internal_links = []
        external_links = []

        for a in soup.find_all("a", href=True):
            raw_href = a["href"].strip()

            if not raw_href or raw_href.startswith(
                ("#", "javascript:", "mailto:", "tel:")
            ):
                continue

            full_url = urljoin(url, raw_href)
            parsed_href = urlparse(full_url)

            # Drop fragment
            clean_url = (
                f"{parsed_href.scheme}://"
                f"{parsed_href.netloc}"
                f"{parsed_href.path}"
            )

            if parsed_href.query:
                clean_url += f"?{parsed_href.query}"

            if parsed_href.netloc.lower() == self.domain:
                internal_links.append(clean_url)
            else:
                external_links.append(clean_url)

        # Images
        images = []

        for img in soup.find_all("img"):
            src = img.get("src") or ""
            alt = img.get("alt") or ""

            images.append({
                "src": urljoin(url, src),
                "alt": alt.strip()
            })

        # Re-parse raw html to extract scripts and JSON-LD
        full_soup = BeautifulSoup(
            html,
            "html.parser"
        )

        raw_json_ld = []

        for tag in full_soup.find_all(
            "script",
            type="application/ld+json"
        ):
            if tag.string:
                raw_json_ld.append(
                    tag.string.strip()
                )

        p_type = classify_page(
            url,
            title,
            h1s,
            h2s,
            text,
            html,
            raw_json_ld,
            internal_links
        )

        return PageData(
            url=url,
            status_code=status_code,
            raw_html=html,
            text_content=text,
            title=title,
            meta_description=meta_desc,
            meta_robots=meta_robots,
            canonical_url=canonical_url,
            h1_tags=h1s,
            h2_tags=h2s,
            internal_links=list(
                dict.fromkeys(internal_links)
            ),
            external_links=list(
                dict.fromkeys(external_links)
            ),
            images=images,
            json_ld_raw=raw_json_ld,
            page_type=p_type,
            depth=depth,
            response_headers=dict(headers)
        )

    def crawl(self) -> CrawlSummary:
        start_time = time.time()

        self.fetch_robots()
        llms_txt_found, llms_txt_content = self.fetch_llms_txt()
        summary = CrawlSummary(
            target_domain=self.domain,
            start_url=self.base_url,
            crawled_at=time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime()
            ),
            robots_txt_found=bool(
                self.robots_checker
                and self.robots_checker.robots_text
            ),
            robots_txt_content=(
                self.robots_checker.robots_text
                if self.robots_checker
                else ""
            ),
            llms_txt_found=llms_txt_found,
            llms_txt_content=llms_txt_content,
            site_type="",
            crawl_duration_seconds=0.0,
            pages_skipped=0,
            robots_blocked_urls=[]
        )

        visited: Set[str] = set()

        # Priority queue structure:
        # list of (priority, depth, url)
        queue: List[Tuple[int, int, str]] = [
            (100, 0, self.base_url)
        ]

        while queue and len(summary.pages) < self.max_pages:

            # Sort queue so highest priority comes first
            queue.sort(
                key=lambda x: x[0],
                reverse=True
            )

            priority, depth, current_url = queue.pop(0)

            normalized_url = normalize_url(
                current_url
            )

            if normalized_url in visited:
                continue

            visited.add(normalized_url)

            # Respect robots.txt
            parsed_current = urlparse(
                current_url
            )

            if (
                self.robots_checker
                and not self.robots_checker.is_allowed(
                    parsed_current.path or "/"
                )
            ):
                summary.robots_blocked_urls.append(
                    current_url
                )

                summary.pages_skipped += 1
                continue

            try:
                resp = self.session.get(
                    current_url,
                    timeout=self.timeout,
                    allow_redirects=True
                )

                # Ensure we only parse HTML
                content_type = resp.headers.get(
                    "Content-Type",
                    ""
                ).lower()

                if (
                    "text/html" not in content_type
                    and "application/xhtml" not in content_type
                ):
                    continue

                page_data = self.parse_page(
                    url=resp.url,
                    html=resp.text,
                    status_code=resp.status_code,
                    depth=depth,
                    headers=resp.headers
                )

                summary.pages.append(
                    page_data
                )

                # Queue internal links if within max_depth
                if depth < self.max_depth:

                    for link in page_data.internal_links:

                        norm_link = normalize_url(
                            link
                        )

                        already_queued = any(
                            norm_link
                            == normalize_url(item[2])
                            for item in queue
                        )

                        if (
                            norm_link not in visited
                            and not already_queued
                        ):
                            prio = calculate_url_priority(
                                link
                            )

                            queue.append(
                                (
                                    prio,
                                    depth + 1,
                                    link
                                )
                            )

            except requests.RequestException as e:
                summary.crawl_errors.append({
                    "url": current_url,
                    "error": str(e)
                })

        summary.crawl_duration_seconds = (
            time.time() - start_time
        )

        summary.site_type = classify_site(
            summary.pages,
            self.domain
        )

        return summary