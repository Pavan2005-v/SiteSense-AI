"""
URL normalization utilities for consistent URL handling across the audit pipeline.
Ensures affected_urls, evidence references, and deduplication use identical URL forms.
"""
from urllib.parse import urlparse, urlunparse, urljoin, parse_qs, urlencode
from typing import List, Set


def normalize_url(url: str) -> str:
    """
    Normalizes a URL to a canonical form for consistent comparison.
    - Lowercases scheme and host
    - Removes fragments
    - Removes trailing slashes (except for root path)
    - Sorts query parameters
    - Strips default ports
    """
    if not url:
        return url
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Normalize path — remove trailing slash unless root
    path = parsed.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if not path:
        path = "/"

    # Sort query parameters for consistency
    query = ""
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        sorted_params = sorted(params.items())
        query = urlencode(sorted_params, doseq=True)

    # Drop fragment entirely
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def dedupe_urls(urls: List[str]) -> List[str]:
    """Normalizes and deduplicates a list of URLs, preserving order."""
    seen: Set[str] = set()
    result: List[str] = []
    for url in urls:
        norm = normalize_url(url)
        if norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def urls_belong_to_domain(urls: List[str], domain: str) -> List[str]:
    """Returns only URLs that belong to the given domain (case-insensitive)."""
    domain_lower = domain.lower().lstrip("www.")
    valid = []
    for url in urls:
        parsed = urlparse(url)
        host = parsed.netloc.lower().lstrip("www.")
        if host == domain_lower or host.endswith("." + domain_lower):
            valid.append(url)
    return valid


def extract_domain(url: str) -> str:
    """Extracts the domain (netloc) from a URL."""
    return urlparse(url).netloc.lower()
