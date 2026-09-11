"""
Multi-signal page-type classifier.
Uses URL path, title, headings, structured data, content patterns, and links
to classify pages rather than relying on URL keywords alone.
"""
from typing import List, Optional, Any
from urllib.parse import urlparse
import re
import json


# Page types supported
PAGE_TYPES = [
    "homepage", "about", "product_detail", "product_listing", "service",
    "pricing", "contact", "article", "documentation", "legal", "privacy",
    "terms", "location", "search", "landing", "category", "general"
]

# Legal/policy page indicators
LEGAL_KEYWORDS = {"privacy", "policy", "policies", "legal", "disclaimer",
                  "cookie", "cookies", "gdpr", "ccpa", "data-protection",
                  "data protection"}
TERMS_KEYWORDS = {"terms", "conditions", "tos", "terms-of-service",
                  "terms-of-use", "acceptable-use", "eula", "agreement"}

# Page type signals by keyword clusters
_PRODUCT_DETAIL_SIGNALS = {"add to cart", "buy now", "add to bag", "in stock",
                           "out of stock", "quantity", "sku:", "item #", "product details"}
_PRODUCT_LISTING_SIGNALS = {"showing results", "sort by", "filter by", "items found",
                            "products found", "browse all", "view all"}


def classify_page(url: str, title: str = "", h1_tags: List[str] = None,
                  h2_tags: List[str] = None, text_content: str = "",
                  raw_html: str = "", json_ld_raw: List[str] = None,
                  internal_links: List[str] = None) -> str:
    """
    Classifies a page using multiple signals. Returns one of PAGE_TYPES.
    Signal priority: structured data > content patterns > headings > URL/title keywords.
    """
    if h1_tags is None:
        h1_tags = []
    if h2_tags is None:
        h2_tags = []
    if json_ld_raw is None:
        json_ld_raw = []
    if internal_links is None:
        internal_links = []

    parsed = urlparse(url)
    path = parsed.path.strip("/").lower()
    path_segments = [s for s in path.split("/") if s]
    title_lower = (title or "").lower()
    text_lower = (text_content or "").lower()[:3000]  # First 3000 chars for efficiency
    all_headings = " ".join(h1_tags + h2_tags).lower()

    # 1. HOMEPAGE — empty path or index
    if not path or path in ("", "index.html", "index.htm", "index.php", "home"):
        return "homepage"

    # 2. STRUCTURED DATA signals (strongest signal)
    schema_types = _extract_schema_types(json_ld_raw)
    if any(t in schema_types for t in ("product",)):
        # Verify it's actually a detail page, not a listing
        if _has_product_detail_content(text_lower):
            return "product_detail"
    if "faqpage" in schema_types or "qapage" in schema_types:
        return "documentation"
    if "article" in schema_types or "newsarticle" in schema_types or "blogposting" in schema_types:
        return "article"

    # 3. LEGAL / PRIVACY / TERMS — check URL and content
    if _matches_any(path_segments, LEGAL_KEYWORDS) or _matches_any(title_lower.split(), LEGAL_KEYWORDS):
        return "legal"
    if _matches_any(path_segments, {"privacy"}) or "privacy" in title_lower:
        return "privacy"
    if _matches_any(path_segments, TERMS_KEYWORDS) or _matches_any(title_lower.split(), TERMS_KEYWORDS):
        return "terms"

    # 4. CONTENT PATTERN signals
    if _has_product_detail_content(text_lower):
        return "product_detail"
    if _has_product_listing_content(text_lower, internal_links):
        return "product_listing"

    # 5. URL + TITLE keyword signals (weakest, used as fallback)
    combined = f"{path} {title_lower}"
    if any(k in combined for k in ("about", "company", "team", "who-we-are", "mission", "our-story")):
        return "about"
    if any(k in combined for k in ("pricing", "plans", "subscription", "cost", "tier")):
        return "pricing"
    if any(k in combined for k in ("contact", "reach-us", "get-in-touch")):
        return "contact"
    if any(k in combined for k in ("location", "store-locator", "find-us", "branches")):
        return "location"
    if any(k in combined for k in ("search", "results", "query")):
        return "search"
    if any(k in combined for k in ("service", "solution", "offering", "capability")):
        return "service"
    if any(k in combined for k in ("blog", "article", "news", "post", "insights", "journal")):
        return "article"
    if any(k in combined for k in ("doc", "guide", "manual", "api", "reference", "help", "tutorial", "faq")):
        return "documentation"
    if any(k in combined for k in ("category", "categories", "collections", "shop", "catalog")):
        return "category"

    return "general"


def is_conversion_page(page_type: str) -> bool:
    """Returns True if the page type is one where CTA checks are meaningful."""
    return page_type in ("homepage", "product_detail", "pricing", "service", "landing")


def is_legal_page(page_type: str) -> bool:
    """Returns True if the page is a legal/policy/terms page."""
    return page_type in ("legal", "privacy", "terms")


def is_content_page(page_type: str) -> bool:
    """Returns True if this page is primarily informational content."""
    return page_type in ("article", "documentation", "about", "general")


def _extract_schema_types(json_ld_raw: List[str]) -> set:
    """Extract lowercase @type values from JSON-LD blocks."""
    types = set()
    for raw in json_ld_raw:
        try:
            data = json.loads(raw)
            _collect_types(data, types)
        except Exception:
            pass
    return types


def _collect_types(data, types: set):
    if isinstance(data, list):
        for item in data:
            _collect_types(item, types)
    elif isinstance(data, dict):
        if "@graph" in data:
            _collect_types(data["@graph"], types)
        t = data.get("@type", "")
        if isinstance(t, list):
            for item in t:
                types.add(str(item).lower())
        elif t:
            types.add(str(t).lower())


def _has_product_detail_content(text_lower: str) -> bool:
    """Check if page content looks like a product detail page."""
    matches = sum(1 for sig in _PRODUCT_DETAIL_SIGNALS if sig in text_lower)
    return matches >= 2


def _has_product_listing_content(text_lower: str, internal_links: List[str]) -> bool:
    """Check if page content looks like a product listing/category page."""
    matches = sum(1 for sig in _PRODUCT_LISTING_SIGNALS if sig in text_lower)
    # Listings typically have many internal links to product pages
    has_many_links = len(internal_links) > 10
    return matches >= 1 and has_many_links


def _matches_any(segments, keywords: set) -> bool:
    """Check if any segment matches any keyword."""
    for seg in segments:
        clean = seg.lower().replace("-", " ").replace("_", " ")
        if clean in keywords or any(kw in clean for kw in keywords):
            return True
    return False
