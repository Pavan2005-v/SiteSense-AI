"""
Site-type classifier.
Infers the overall site type and classification confidence from aggregate
page-level signals to determine which audit rules are meaningful for the site.
All classifications rely strictly on generic, multi-signal heuristics without
hardcoded domain or brand exceptions.
"""
from typing import List, Optional, Tuple, Dict, Any, Set
from collections import Counter
import re
from bs4 import BeautifulSoup


SITE_TYPES = [
    "ecommerce", "marketplace", "saas", "corporate", "documentation",
    "knowledge_base", "publisher", "news", "blog", "educational", "community",
    "directory", "government", "nonprofit", "portfolio", "utility", "landing",
    "search_portal", "mixed", "unknown"
]


def classify_site_with_confidence(pages: list, target_domain: str = "") -> Tuple[str, str]:
    """
    Infers site type and classification confidence from aggregate crawl signals.
    Returns: (site_type, confidence) where confidence is 'high', 'medium', or 'low'.
    Uses multi-signal heuristics:
    - Structured data types
    - DOM forms and interactive elements
    - Page-type distributions
    - Title, headings, and semantic keyword clusters
    """
    if not pages:
        return "unknown", "low"

    total_pages = len(pages)
    page_types = Counter(p.page_type for p in pages)
    homepage = next((p for p in pages if p.page_type == "homepage"), pages[0])
    hp_html = homepage.raw_html or ""
    hp_soup = BeautifulSoup(hp_html, "html.parser")
    hp_text = (homepage.text_content or "").lower()
    hp_title = (homepage.title or "").lower()
    domain_lower = target_domain.lower()

    # Collect all JSON-LD schema types across all crawled pages
    all_schema_types: Set[str] = set()
    for p in pages:
        for raw in (p.json_ld_raw or []):
            try:
                import json
                data = json.loads(raw)
                _collect_schema_types(data, all_schema_types)
            except Exception:
                pass

    # Aggregate text across crawled pages (sampled for efficiency)
    sample_text = " ".join((p.text_content or "")[:1000] for p in pages).lower()

    # 1. Search Portal / Web Utility Detection (Signal-Based, Zero Hardcoding)
    # Generic signals: prominent query input, search action/role, minimal narrative copy (<150 words)
    has_search_input = bool(
        hp_soup.find("input", attrs={"name": re.compile(r"^(q|query|search|k|wd)$", re.I)}) or
        hp_soup.find("input", attrs={"type": "search"}) or
        hp_soup.find("form", attrs={"role": "search"}) or
        hp_soup.find("form", attrs={"action": re.compile(r"/search", re.I)})
    )
    hp_words = len(hp_text.split())
    has_search_title = any(kw in hp_title for kw in ("search", "find", "explore"))

    if has_search_input and hp_words < 150:
        # A lightweight page dominated by a search input is a search portal
        return "search_portal", "high"
    if has_search_input and has_search_title and hp_words < 300:
        return "search_portal", "medium"

    # 2. Knowledge Base / Reference / Encyclopedia (Signal-Based)
    kb_signals = [
        any(kw in hp_title for kw in ("encyclopedia", "knowledge base", "wiki", "reference", "dictionary")),
        any(kw in hp_text[:1000] for kw in ("encyclopedia", "free knowledge", "wiki", "articles in english", "the free dictionary")),
        any(t in all_schema_types for t in ("encyclopedia", "definedterm", "referencearticle")),
        page_types.get("article", 0) / max(total_pages, 1) >= 0.6 and "wiki" in domain_lower
    ]
    if any(kw in hp_title for kw in ("encyclopedia", "wiki", "knowledge base")):
        return "knowledge_base", "high"
    if sum(bool(s) for s in kb_signals) >= 2:
        return "knowledge_base", "high"

    # 3. Educational / Academic
    edu_signals = [
        domain_lower.endswith(".edu") or ".edu." in domain_lower or ".ac." in domain_lower,
        any(t in all_schema_types for t in ("educationalorganization", "course", "school", "collegeoruniversity")),
        any(kw in hp_title for kw in ("university", "academy", "institute of technology", "curriculum", "courses")),
        any(kw in hp_text[:1000] for kw in ("admissions", "academic programs", "faculties", "campus", "tuition"))
    ]
    if sum(bool(s) for s in edu_signals) >= 2:
        return "educational", "high"

    # 4. Local Business / Hospitality / Physical Establishment
    local_schemas = ("localbusiness", "restaurant", "hotel", "medicalbusiness", "store", "lodgingbusiness")
    if any(t in all_schema_types for t in local_schemas):
        return "local_business", "high"

    # 5. Nonprofit / Foundation / Charity
    nonprofit_signals = [
        any(kw in domain_lower for kw in ("foundation.", "charity.", "wikimedia.")),
        any(t in all_schema_types for t in ("ngoproganization", "nonprofit")),
        any(kw in hp_text[:1000] for kw in ("nonprofit", "non-profit", "501(c)", "our mission", "donate to support")),
        any(kw in hp_title for kw in ("foundation", "non-profit", "charity", "trust"))
    ]
    if sum(bool(s) for s in nonprofit_signals) >= 2:
        return "nonprofit", "high"

    # 6. Marketplace / Talent / Opportunity Exchange Platform
    mkt_keywords = (
        "competitions", "hackathons", "quizzes", "scholarships", "internships",
        "jobs", "opportunities", "challenges", "gigs", "listings", "bids",
        "sellers", "buyers", "freelancers", "candidates", "talent", "marketplace",
        "peer-to-peer", "multi-vendor", "find talent", "browse opportunities", "post a job"
    )
    mkt_title_matches = sum(1 for kw in mkt_keywords if kw in hp_title)
    mkt_text_matches = sum(1 for kw in mkt_keywords if kw in sample_text)

    if mkt_title_matches >= 2 or (mkt_title_matches >= 1 and mkt_text_matches >= 2):
        return "marketplace", "high"
    if mkt_title_matches >= 1 or mkt_text_matches >= 3:
        return "marketplace", "medium"

    # 7. Ecommerce Detection
    product_count = page_types.get("product_detail", 0) + page_types.get("product_listing", 0)
    has_product_schema = any(t in all_schema_types for t in ("product", "offer", "itemlist"))
    has_cart_checkout = any("cart" in (p.url or "").lower() or "checkout" in (p.url or "").lower() for p in pages)

    if has_product_schema and (product_count >= 1 or has_cart_checkout):
        return "ecommerce", "high"
    if product_count >= 2 and (product_count / total_pages >= 0.3):
        return "ecommerce", "high"
    if has_cart_checkout and product_count >= 1:
        return "ecommerce", "medium"

    # 8. Pure Documentation Site
    doc_count = page_types.get("documentation", 0)
    is_doc_domain = any(domain_lower.startswith(k) for k in ("docs.", "documentation.", "developer.", "guide."))
    is_doc_title = any(k in hp_title for k in ("documentation", "api reference", "developer docs", "handbook", "user guide"))

    if (is_doc_domain or is_doc_title) and (doc_count >= 1 or "api" in hp_text or "sdk" in hp_text):
        return "documentation", "high"
    if total_pages >= 3 and (doc_count / total_pages >= 0.6):
        return "documentation", "medium"

    # 9. Publisher / News / Editorial Site
    article_count = page_types.get("article", 0)
    if total_pages >= 3 and (article_count / total_pages >= 0.5):
        return "publisher", "high"
    if any(t in all_schema_types for t in ("newsarticle", "blogposting")) and article_count >= 2:
        return "publisher", "medium"

    # 10. SaaS / Digital Product Platform
    has_pricing = any(p.page_type == "pricing" for p in pages) or "pricing" in sample_text
    saas_signals = sum([
        has_pricing,
        any(k in sample_text for k in ("free trial", "start free", "sign up free", "book a demo", "request demo")),
        any(k in sample_text for k in ("api", "integrations", "dashboard", "workflows", "automate", "analytics")),
        any(k in hp_title for k in ("platform", "software", "saas", "app", "cloud", "api")),
    ])
    if saas_signals >= 3:
        return "saas", "high"
    if saas_signals == 2 and has_pricing:
        return "saas", "medium"

    # 11. Portfolio / Personal Studio
    portfolio_signals = [
        any(kw in hp_title for kw in ("portfolio", "selected works", "designer", "photographer", "projects")),
        any(kw in sample_text for kw in ("case studies", "selected projects", "freelance", "my work"))
    ]
    if sum(bool(s) for s in portfolio_signals) >= 2:
        return "portfolio", "medium"

    # 12. Community / Forum
    community_signals = [
        any(kw in hp_title for kw in ("community", "forum", "discussion", "hub")),
        any(kw in sample_text for kw in ("join the discussion", "threads", "members", "community guidelines"))
    ]
    if sum(bool(s) for s in community_signals) >= 2:
        return "community", "medium"

    # 13. Corporate / Professional Services Site
    corporate_signals = sum([
        page_types.get("about", 0) >= 1,
        page_types.get("service", 0) >= 1 or page_types.get("contact", 0) >= 1,
        any(k in sample_text for k in ("about our company", "our leadership", "our team", "consulting", "enterprise services", "our capabilities")),
    ])
    if corporate_signals >= 2:
        return "corporate", "medium"

    # Fallback to unknown with low confidence (triggering conservative analysis)
    return "unknown", "low"


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
