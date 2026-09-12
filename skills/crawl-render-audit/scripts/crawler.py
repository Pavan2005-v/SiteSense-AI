"""
Bounded Polite Crawler for Brand AI-Readiness and Engagement Auditing.
Safely extracts HTML, structure, headers, links, images, and JSON-LD from targeted domains.
Supports adaptive prioritized BFS, subdomain scoping, robots.txt per-host caching,
response size limits, and comprehensive crawl metric accounting.
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
import re
import time
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

from skills.common.models import PageData, CrawlSummary
from skills.common.page_classifier import classify_page
from skills.common.site_classifier import classify_site
from skills.common.url_utils import normalize_url, is_internal_link, is_safe_url, get_registered_domain
from .robots_checker import RobotsChecker


USER_AGENT = "AdobeBrandReadinessAuditor/1.0 (+https://adobe.com/hackathon-2026; read-only bot)"
REQUEST_TIMEOUT = 6.0
MAX_PAGES_DEFAULT = 12
MAX_DEPTH_DEFAULT = 2
MAX_RESPONSE_SIZE = 2 * 1024 * 1024  # 2MB max response to prevent memory exhaustion
OVERALL_CRAWL_TIMEOUT = 55.0          # Max total seconds allowed for entire crawl


def calculate_url_priority(url: str, target_host: str) -> int:
    """
    Assigns priority weight to URLs to ensure high-value pages are crawled first.
    Homepage & exact host links are prioritized over secondary subdomains.
    """
    u = url.lower()
    parsed = urlparse(u)
    path = parsed.path.strip("/").lower()
    host = parsed.netloc.lower().split(":")[0]

    # Host preference: exact host gets bonus over cross-subdomain
    host_bonus = 15 if host == target_host.lower().split(":")[0] else 0

    if not path or path in ("", "index.html", "index.htm", "index.php", "home"):
        return 100 + host_bonus

    # Keyword prioritization
    priority_keywords = [
        ("about", 85),
        ("product", 80),
        ("pricing", 80),
        ("service", 75),
        ("solution", 75),
        ("wiki/main_page", 90),
        ("contact", 70),
        ("feature", 65),
        ("docs", 60),
        ("guide", 60),
        ("blog", 50),
        ("category", 45),
        ("article", 45),
    ]
    for keyword, score in priority_keywords:
        if keyword in u:
            return score + host_bonus

    # English / primary portal preference for multilingual domains
    if host.startswith("en."):
        return 40 + host_bonus

    return 30 + host_bonus


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
        self.base_url = normalize_url(base_url)
        parsed = urlparse(self.base_url)
        self.domain = parsed.netloc.lower().split(":")[0]
        self.scheme = parsed.scheme or "https"
        self.registered_domain = get_registered_domain(self.domain)
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout

        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

        # Cache RobotsChecker instances per host: host -> RobotsChecker
        self.robots_cache: Dict[str, RobotsChecker] = {}

    def get_robots_checker(self, host: str, scheme: str = "https") -> RobotsChecker:
        """Retrieves or fetches robots.txt for a specific host."""
        host_clean = host.lower().split(":")[0]
        if host_clean in self.robots_cache:
            return self.robots_cache[host_clean]

        robots_url = f"{scheme}://{host_clean}/robots.txt"
        try:
            resp = self.session.get(robots_url, timeout=self.timeout)
            if resp.status_code == 200:
                checker = RobotsChecker(f"{scheme}://{host_clean}", resp.text)
                self.robots_cache[host_clean] = checker
                return checker
        except Exception:
            pass

        checker = RobotsChecker(f"{scheme}://{host_clean}", "")
        self.robots_cache[host_clean] = checker
        return checker

    def parse_page(self, url: str, html: str, status_code: int, depth: int, headers: Dict[str, str]) -> PageData:
        soup = BeautifulSoup(html, "html.parser")

        # Clean copy for text extraction
        soup_clean = BeautifulSoup(html, "html.parser")
        for element in soup_clean(["script", "style", "noscript", "svg", "iframe"]):
            element.extract()
        text = soup_clean.get_text(separator=" ", strip=True)

        # Title & Meta
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        meta_robots = ""
        canonical_url = None

        meta_d = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if meta_d:
            meta_desc = (meta_d.get("content") or "").strip()

        meta_r = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
        if meta_r:
            meta_robots = (meta_r.get("content") or "").strip()

        canonical = soup.find("link", rel=re.compile(r"canonical", re.I))
        if canonical:
            canonical_url = (canonical.get("href") or "").strip()

        # Headings
        h1s = [h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]

        # Links (Internal vs External with subdomain awareness)
        internal_links = []
        external_links = []
        for a in soup.find_all("a", href=True):
            raw_href = a["href"].strip()
            if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(url, raw_href)
            if not is_safe_url(full_url):
                continue
            norm = normalize_url(full_url)
            if is_internal_link(norm, self.domain, allow_subdomains=True):
                internal_links.append(norm)
            else:
                external_links.append(norm)

        # Images
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or ""
            alt = img.get("alt") or ""
            images.append({"src": urljoin(url, src), "alt": alt.strip()})

        # JSON-LD raw strings
        raw_json_ld = []
        for tag in soup.find_all("script", type="application/ld+json"):
            if tag.string:
                raw_json_ld.append(tag.string.strip())

        # Check for SPA shell or client-side challenge
        html_lower = html.lower()
        text_lower = text.lower()
        is_spa_mount = bool(
            soup.find(id=re.compile(r"^(root|app|__next)$", re.I)) or
            soup.find("app-root") or
            soup.find(attrs={"id": re.compile(r"^app$", re.I)})
        )
        is_challenge = bool(
            "window.prerenderready" in html_lower or
            "prerenderready" in html_lower or
            "cookies disabled" in text_lower or
            "please wait" in text_lower or
            "enable cookies" in text_lower or
            "enable javascript" in html_lower or
            "your browser does not support javascript" in html_lower
        )
        words = text.split()
        is_spa_shell = bool((is_spa_mount or is_challenge) and len(words) < 200 and len(soup.find_all("script")) > 0)
        interactive_count = len(soup.find_all(["button", "a", "input", "form"]))

        p_type = classify_page(url, title, h1s, h2s, text, html, raw_json_ld, internal_links)

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
            internal_links=list(dict.fromkeys(internal_links)),
            external_links=list(dict.fromkeys(external_links)),
            images=images,
            json_ld_raw=raw_json_ld,
            page_type=p_type,
            depth=depth,
            response_headers=dict(headers),
            is_spa_shell=is_spa_shell,
            has_interstitial_challenge=is_challenge,
            interactive_elements_count=interactive_count,
            word_count=len(words)
        )

    def crawl(self) -> CrawlSummary:
        start_time = time.time()
        primary_robots = self.get_robots_checker(self.domain, self.scheme)

        rejection_reasons = defaultdict(int)
        discovered_urls: Set[str] = {normalize_url(self.base_url)}
        skipped_urls: Dict[str, str] = {}

        summary = CrawlSummary(
            target_domain=self.domain,
            start_url=self.base_url,
            crawled_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            robots_txt_found=bool(primary_robots and primary_robots.robots_text),
            robots_txt_content=primary_robots.robots_text if primary_robots else "",
            site_type="other",
            crawl_duration_seconds=0.0,
            pages_discovered=1,
            pages_queued=1,
            pages_fetched=0,
            pages_skipped=0,
            rejection_reasons={},
            skipped_urls={},
            robots_blocked_urls=[],
            crawl_limitations=[]
        )

        visited: Set[str] = set()
        # Priority queue structure: list of (priority, depth, url)
        queue: List[Tuple[int, int, str]] = [(100, 0, self.base_url)]

        while queue and len(summary.pages) < self.max_pages:
            # Check overall crawl timeout
            if (time.time() - start_time) > OVERALL_CRAWL_TIMEOUT:
                summary.crawl_limitations.append(
                    f"Bounded crawl sampling: completed inspection of {len(summary.pages)} priority pages within time budget ({time.time() - start_time:.1f}s, discovered {len(discovered_urls)} total candidate URLs)."
                )
                break

            # Highest priority URL popped first
            queue.sort(key=lambda x: x[0], reverse=True)
            priority, depth, current_url = queue.pop(0)

            normalized_url = normalize_url(current_url)
            if normalized_url in visited:
                rejection_reasons["already_visited"] += 1
                continue
            visited.add(normalized_url)

            # SSRF safety check
            if not is_safe_url(current_url):
                rejection_reasons["unsafe_url_ssrf"] += 1
                skipped_urls[current_url] = "unsafe_url_ssrf"
                summary.pages_skipped += 1
                continue

            # Check robots.txt for current page's host
            parsed_current = urlparse(current_url)
            page_host = parsed_current.netloc.lower().split(":")[0]
            host_robots = self.get_robots_checker(page_host, parsed_current.scheme or self.scheme)

            if host_robots and not host_robots.is_allowed(parsed_current.path or "/"):
                summary.robots_blocked_urls.append(current_url)
                summary.pages_skipped += 1
                skipped_urls[current_url] = "robots_txt_disallowed"
                rejection_reasons["robots_txt_disallowed"] += 1
                continue

            try:
                resp = self.session.get(
                    current_url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=True
                )

                # SSRF & redirect security: verify all intermediate and final URLs
                is_redirect_safe = True
                if resp.history:
                    if len(resp.history) > 5:
                        rejection_reasons["too_many_redirects"] += 1
                        skipped_urls[current_url] = "too_many_redirects"
                        summary.pages_skipped += 1
                        continue
                    for r in resp.history:
                        if not is_safe_url(r.url):
                            is_redirect_safe = False
                            break

                if not is_redirect_safe or not is_safe_url(resp.url):
                    rejection_reasons["unsafe_redirect_ssrf"] += 1
                    skipped_urls[current_url] = "unsafe_redirect_ssrf"
                    summary.pages_skipped += 1
                    continue

                # Update target domain if start_url was redirected to canonical host
                if depth == 0 and resp.url:
                    final_parsed = urlparse(resp.url)
                    final_host = final_parsed.netloc.lower().split(":")[0]
                    if final_host != self.domain and is_internal_link(resp.url, self.domain):
                        self.domain = final_host
                        summary.target_domain = final_host

                # Content-Type check: only process HTML
                content_type = resp.headers.get("Content-Type", "").lower()
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    rejection_reasons["non_html_content"] += 1
                    skipped_urls[current_url] = f"non_html_content_{content_type}"
                    summary.pages_skipped += 1
                    continue

                # Read bounded response body
                content_chunks = []
                bytes_read = 0
                for chunk in resp.iter_content(chunk_size=16384, decode_unicode=True):
                    content_chunks.append(chunk)
                    bytes_read += len(chunk.encode("utf-8", errors="ignore"))
                    if bytes_read >= MAX_RESPONSE_SIZE:
                        break
                html_text = "".join(content_chunks)

                page_data = self.parse_page(
                    url=resp.url,
                    html=html_text,
                    status_code=resp.status_code,
                    depth=depth,
                    headers=resp.headers
                )
                summary.pages.append(page_data)
                summary.pages_fetched += 1

                # Discover and queue internal links if within max_depth and queue budget
                if depth < self.max_depth:
                    for link in page_data.internal_links:
                        norm_link = normalize_url(link)
                        discovered_urls.add(norm_link)
                        if norm_link not in visited and not any(norm_link == normalize_url(item[2]) for item in queue):
                            if len(queue) < 500:
                                prio = calculate_url_priority(link, self.domain)
                                queue.append((prio, depth + 1, link))

            except requests.RequestException as e:
                summary.crawl_errors.append({"url": current_url, "error": str(e)})
                rejection_reasons["fetch_error"] += 1
                skipped_urls[current_url] = f"fetch_error_{str(e)[:40]}"
                summary.pages_skipped += 1

        summary.crawl_duration_seconds = time.time() - start_time
        summary.pages_discovered = len(discovered_urls)
        summary.pages_queued = len(visited) + len(queue)
        summary.rejection_reasons = dict(rejection_reasons)
        summary.skipped_urls = dict(skipped_urls)
        if summary.pages:
            summary.site_type = classify_site(summary.pages, self.domain)
        else:
            summary.site_type = "unknown"

        return summary
