"""
Site-type classifier.
Infers the overall site type and classification confidence from aggregate
page-level signals to determine which audit rules are meaningful for the site.
"""
from typing import List, Optional, Tuple, Dict, Any
from collections import Counter
import re
from bs4 import BeautifulSoup


SITE_TYPES = [
    "ecommerce", "corporate", "saas", "publisher", "documentation",
    "search_portal", "portfolio", "local_business", "nonprofit", "marketplace", "other"
]


def classify_site_with_confidence(pages: list, target_domain: str = "") -> Tuple[str, str]:
    """
    Infers site type and classification confidence from aggregate crawl signals.
    Returns: (site_type, confidence) where confidence is 'high', 'medium', or 'low'.
    """
    if not pages:
        return "other", "low"

    total_pages = len(pages)
    page_types = Counter(p.page_type for p in pages)
    homepage = next((p for p in pages if p.page_type == "homepage"), pages[0])
    hp_html = homepage.raw_html or ""
    hp_soup = BeautifulSoup(hp_html, "html.parser")
    hp_text = (homepage.text_content or "").lower()
    hp_title = (homepage.title or "").lower()
    domain_lower = target_domain.lower()

    # 1. Search Engine / Web Portal Detection
    # Look for primary search utility on homepage
    has_prominent_search_form = bool(
        hp_soup.find("input", attrs={"name": re.compile(r"^(q|query|search|k|wd)$", re.I)}) or
        hp_soup.find("form", attrs={"role": "search", "action": re.compile(r"search", re.I)})
    )
    is_search_brand = any(kw in domain_lower for kw in ["google.", "bing.", "duckduckgo.", "yahoo.", "baidu."])
    if is_search_brand or (has_prominent_search_form and len(hp_text.split()) < 120 and "search" in hp_title):
        return "search_portal", "high"

    # Extract all JSON-LD schema types across site
    all_schema_types = set()
    for p in pages:
        for raw in (p.json_ld_raw or []):
            try:
                import json
                data = json.loads(raw)
                _collect_schema_types(data, all_schema_types)
            except Exception:
                pass

    # 2. Local Business / Hospitality
    if any(t in all_schema_types for t in ("localbusiness", "restaurant", "hotel", "medicalbusiness")):
        return "local_business", "high"

    # 3. Ecommerce Detection
    product_count = page_types.get("product_detail", 0) + page_types.get("product_listing", 0)
    has_product_schema = any(t in all_schema_types for t in ("product", "offer", "itemlist"))
    has_cart_checkout = any("cart" in (p.url or "").lower() or "checkout" in (p.url or "").lower() for p in pages)
    
    if has_product_schema and (product_count >= 1 or has_cart_checkout):
        return "ecommerce", "high"
    if product_count >= 2 and (product_count / total_pages >= 0.3):
        return "ecommerce", "high"

    # 4. Pure Documentation Site
    # Requires documentation to be the predominant purpose, NOT just having a help link
    doc_count = page_types.get("documentation", 0)
    is_doc_domain = any(k in domain_lower for k in ("docs.", "documentation.", "developer.", "guide."))
    is_doc_title = any(k in hp_title for k in ("documentation", "api reference", "developer docs", "handbook"))

    if (is_doc_domain or is_doc_title) and (doc_count >= 1 or "doc" in hp_text):
        return "documentation", "high"
    if total_pages >= 3 and (doc_count / total_pages >= 0.6):
        return "documentation", "medium"

    # 5. Publisher / News / Editorial Site
    article_count = page_types.get("article", 0)
    if total_pages >= 3 and (article_count / total_pages >= 0.5):
        return "publisher", "high"
    if any(t in all_schema_types for t in ("newsarticle", "blogposting")) and article_count >= 2:
        return "publisher", "medium"

    # 6. SaaS / Digital Product Platform
    all_text = " ".join((p.text_content or "")[:600] for p in pages).lower()
    has_pricing = any(p.page_type == "pricing" for p in pages) or "pricing" in all_text
    saas_signals = sum([
        has_pricing,
        any(k in all_text for k in ("free trial", "start free", "sign up free", "book a demo", "request demo")),
        any(k in all_text for k in ("api", "integrations", "dashboard", "workflows", "automate")),
        any(k in hp_title for k in ("platform", "software", "saas", "app", "cloud")),
    ])
    if saas_signals >= 3:
        return "saas", "high"
    if saas_signals == 2 and has_pricing:
        return "saas", "medium"

    # 7. Corporate / Professional Services Site
    corporate_signals = sum([
        page_types.get("about", 0) >= 1,
        page_types.get("service", 0) >= 1 or page_types.get("contact", 0) >= 1,
        any(k in all_text for k in ("about our company", "our leadership", "our team", "consulting", "services")),
    ])
    if corporate_signals >= 2:
        return "corporate", "medium"

    # Fallback to Other with Low Confidence
    return "other", "low"


def classify_site(pages: list, target_domain: str = "") -> str:
    """Convenience wrapper returning site_type string."""
    site_type, _ = classify_site_with_confidence(pages, target_domain)
    return site_type


def _collect_schema_types(data, types: set):
    """Recursively collect @type values from JSON-LD."""
    if isinstance(data, list):
        for item in data:
            _collect_schema_types(item, types)
    elif isinstance(data, dict):
        if "@graph" in data:
            _collect_schema_types(data["@graph"], types)
        t = data.get("@type", "")
        if isinstance(t, list):
            for item in t:
                types.add(str(item).lower())
        elif t:
            types.add(str(t).lower())
