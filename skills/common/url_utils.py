"""
URL normalization utilities for consistent URL handling across the audit pipeline.
Ensures affected_urls, evidence references, deduplication, and crawl scoping use identical URL forms.
"""
from urllib.parse import urlparse, urlunparse, urljoin, parse_qs, urlencode
from typing import List, Set
import ipaddress
import re


TWO_PART_TLDS = {
    "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "net.au", "org.au",
    "co.nz", "co.jp", "co.in", "net.in", "org.in", "gen.in", "firm.in",
    "ind.in", "com.br", "com.mx", "com.ar", "com.sg", "co.za"
}


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


def extract_domain(url: str) -> str:
    """Extracts the domain (netloc) from a URL."""
    return urlparse(url).netloc.lower()


def get_registered_domain(host: str) -> str:
    """
    Extracts the registered/apex domain from a hostname.
    E.g.:
      'www.wikipedia.org' -> 'wikipedia.org'
      'en.wikipedia.org' -> 'wikipedia.org'
      'docs.google.com' -> 'google.com'
      'sub.example.co.uk' -> 'example.co.uk'
    """
    host = host.lower().strip().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) <= 2:
        return host

    # Check for known two-part TLDs (e.g. co.uk, com.au)
    last_two = f"{parts[-2]}.{parts[-1]}"
    if last_two in TWO_PART_TLDS and len(parts) >= 3:
        return f"{parts[-3]}.{last_two}"

    return f"{parts[-2]}.{parts[-1]}"


def urls_belong_to_domain(urls: List[str], domain: str) -> List[str]:
    """
    Returns only URLs that belong to the given domain or its subdomains.
    Uses removeprefix('www.') rather than lstrip('www.') to prevent truncating
    domains starting with 'w' (e.g. wikipedia.org, walmart.com).
    """
    clean_domain = domain.lower().strip()
    if clean_domain.startswith("www."):
        clean_domain = clean_domain[4:]

    registered_target = get_registered_domain(clean_domain)
    valid = []

    for url in urls:
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":")[0]
        if host.startswith("www."):
            host_clean = host[4:]
        else:
            host_clean = host

        # Exact match or subdomain match
        if host_clean == clean_domain or host_clean.endswith("." + clean_domain):
            valid.append(url)
        elif get_registered_domain(host) == registered_target:
            valid.append(url)

    return valid


def is_internal_link(url: str, target_host: str, allow_subdomains: bool = True) -> bool:
    """
    Determines if a candidate link belongs to the internal crawl scope of target_host.
    Handles:
    - Same host (exact match)
    - Canonical host variant ('www.' <-> non-www)
    - Subdomains of registered domain when allow_subdomains is True
    """
    parsed = urlparse(url)
    link_host = parsed.netloc.lower().split(":")[0]
    target_clean = target_host.lower().split(":")[0]

    # Exact match
    if link_host == target_clean:
        return True

    # Canonical www variant
    target_no_www = target_clean[4:] if target_clean.startswith("www.") else target_clean
    link_no_www = link_host[4:] if link_host.startswith("www.") else link_host

    if link_no_www == target_no_www:
        return True

    if allow_subdomains:
        # Check if link is a subdomain of the target registered domain
        reg_target = get_registered_domain(target_clean)
        reg_link = get_registered_domain(link_host)
        if reg_link == reg_target:
            return True

    return False


def is_safe_url(url: str) -> bool:
    """
    Security & SSRF verification:
    Ensures URL uses http/https and does not target private, loopback, or cloud-metadata IP addresses.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        host = parsed.netloc.split(":")[0].strip()
        if not host:
            return False

        # Block loopback / localhost names
        if host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"):
            return False

        # Check if host is an IP address
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            # Host is a domain name, which is expected
            pass

        return True
    except Exception:
        return False
