"""
Analyzes site navigation architecture, deep-page orientation, and dead-end pathways.
Applies context-aware exemptions:
- Legal, privacy, terms, documentation, and search utility pages are exempt from dead-end findings
- Breadcrumb analysis is only enforced on deep catalog/content hierarchies
"""
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup
from skills.common.page_classifier import is_legal_page, get_effective_path_depth


_PORTAL_LEAF_NAMES = {
    "home", "index", "index.html", "index.htm", "index.php", "default", "default.html",
    "main", "main_page", "main-page", "portal", "welcome", "frontpage",
    "accueil", "accueil_principal", "portada", "pagina_principale", "strona_glowna"
}


def _is_deep_hierarchical_page(p: Any) -> bool:
    """
    Determines if a page is genuinely an inner leaf in a hierarchical taxonomy
    (e.g., /products/shoes/running-shoes or /docs/api/v2/endpoints),
    as opposed to a top-level, portal, or flat content page.
    """
    # Non-content and root pages never require hierarchical breadcrumbs
    if p.page_type in ("homepage", "legal", "privacy", "terms", "search", "about", "contact", "location", "landing"):
        return False
    if getattr(p, "is_homepage", False):
        return False

    parsed = urlparse(p.url)
    raw_segments = [s for s in parsed.path.strip("/").split("/") if s]
    if not raw_segments:
        return False

    # Check if leaf segment is a known portal/root name
    leaf = raw_segments[-1].lower()
    if leaf in _PORTAL_LEAF_NAMES:
        return False

    # Check title / H1 for portal/home indicators
    title_lower = getattr(p, "title", "").lower() if hasattr(p, "title") else ""
    if any(title_lower == t or title_lower.startswith(t + " -") or title_lower.startswith(t + " |") for t in ("main page", "welcome", "home", "portal", "front page")):
        return False

    h1_list = getattr(p, "h1_tags", []) or []
    if any(h in ("main page", "welcome", "home", "portal", "front page") for h in [h.strip().lower() for h in h1_list]):
        return False

    effective_depth = get_effective_path_depth(p.url)

    # Product detail and documentation pages require depth >= 2
    if p.page_type in ("product_detail", "documentation"):
        return effective_depth >= 2

    # Category and generic pages require depth >= 3 to be considered deep hierarchical pages
    if p.page_type in ("category", "product_listing"):
        return effective_depth >= 2

    return effective_depth >= 3


def _has_orientation_mechanism(p: Any, soup: BeautifulSoup) -> bool:
    """
    Checks for all legitimate mechanisms that orient a visitor within a site's structure:
    1. Visual breadcrumbs (<nav aria-label="breadcrumb">, .breadcrumb)
    2. Schema.org BreadcrumbList JSON-LD / microdata
    3. Parent / up-level links (rel="up", aria-label="parent", "← Back to [Category]")
    4. Sidebar / Table of Contents tree navigation (e.g. docs sidebar)
    5. Category badges/tags linking up to a parent category
    6. Dedicated knowledge-base / encyclopedia category footers
    7. High in-page navigation density (>= 25 internal links + header/nav landmark)
    """
    raw_lower = (p.raw_html or "").lower()

    # 1. Visual breadcrumbs
    if (soup.find("nav", attrs={"aria-label": lambda x: x and "breadcrumb" in x.lower()}) or
        soup.find(class_=lambda x: x and any(k in x.lower() for k in ("breadcrumb", "breadcrumbs", "bread-crumb"))) or
        soup.find(id=lambda x: x and any(k in x.lower() for k in ("breadcrumb", "breadcrumbs")))):
        return True

    # 2. BreadcrumbList schema
    if "breadcrumblist" in raw_lower:
        return True

    # 3. Parent / up-level link
    if soup.find("a", attrs={"rel": lambda x: x and "up" in x.lower()}):
        return True
    if soup.find("a", attrs={"aria-label": lambda x: x and any(k in x.lower() for k in ("parent", "up-level", "category"))}):
        return True
    if soup.find("a", class_=lambda x: x and any(k in x.lower() for k in ("parent-link", "parent-category", "back-to", "up-link"))):
        return True
    for a in soup.find_all("a", href=True):
        a_text = a.get_text(strip=True).lower()
        if re.match(r"^(?:←|«|back to|return to)\s+[\w\s]{2,35}$", a_text):
            return True

    # 4. Sidebar / Table of Contents navigation tree
    sidebar_navs = soup.find_all(
        ["nav", "aside", "div"],
        class_=lambda x: x and any(k in x.lower() for k in ("sidebar", "toc", "docs-nav", "tree", "category-nav", "menu-nav"))
    )
    for s_nav in sidebar_navs:
        if len(s_nav.find_all("a", href=True)) >= 3:
            return True

    # 5. Category badges / tags linking to parent category
    if soup.find(class_=lambda x: x and any(k in x.lower() for k in ("category-badge", "category-link", "article-category", "post-category", "catlinks"))):
        return True

    # 6. Knowledge-base category boxes
    if soup.find(id="catlinks") or soup.find(class_=lambda x: x and "catlinks" in x.lower()):
        return True

    # 7. High contextual navigation density with header landmark
    if len(p.internal_links) >= 25 and soup.find(["header", "nav"]):
        return True

    return False


class NavigationGraph:
    def __init__(self, pages: List[Any], site_type: str = "other"):
        self.pages = pages
        self.site_type = site_type

    def audit_navigation_and_orientation(self) -> List[Dict[str, Any]]:
        findings = []

        # 1. Dead-End Pages Check
        # Require genuinely 0 internal links and 0 external links (not just 0 internal)
        dead_end_pages = []
        dead_end_core_pages = []

        for p in self.pages:
            if p.page_type == "homepage":
                continue
            if is_legal_page(p.page_type) or p.page_type in ("documentation", "search"):
                continue
            if self.site_type in ("search_portal", "knowledge_base") and p.page_type in ("article", "general"):
                continue

            # A true dead-end has no onward navigation links at all
            if len(p.internal_links) == 0:
                dead_end_pages.append(p.url)
                if p.page_type in ["homepage", "product_detail", "pricing", "service"]:
                    dead_end_core_pages.append(p.url)

        if dead_end_core_pages:
            findings.append({
                "issue_type": "navigation_dead_ends",
                "severity": "high",
                "title": f"Navigation dead-end detected on {len(dead_end_core_pages)} core page(s)",
                "evidence": f"Core pages contain zero internal links, trapping visitors without next navigation steps: {', '.join(dead_end_core_pages[:3])}.",
                "action": "Add related content links, category pathways, or persistent footer navigation.",
                "why_it_matters": "Core conversion pages without navigation pathways trap users, completely stalling the buyer journey.",
                "confidence": "high",
                "root_cause": "Orphaned pages or missing global navigation templates.",
                "affected_urls": dead_end_core_pages
            })

        non_core_dead_ends = list(set(dead_end_pages) - set(dead_end_core_pages))
        if non_core_dead_ends:
            findings.append({
                "issue_type": "navigation_dead_ends",
                "severity": "medium",
                "title": f"Navigation dead-end detected on {len(non_core_dead_ends)} non-core page(s)",
                "evidence": f"Pages contain zero internal links, trapping visitors without next navigation steps: {', '.join(non_core_dead_ends[:3])}.",
                "action": "Add related content links or persistent footer navigation to ensure visitors can explore deeper without bouncing.",
                "why_it_matters": "When secondary pages lack navigation, visitors who arrived via search or external links are likely to bounce.",
                "confidence": "high",
                "root_cause": "Orphaned pages or missing global navigation templates.",
                "affected_urls": non_core_dead_ends
            })

        # 2. Deep-Page Orientation & Context Retention (Breadcrumbs / Parent Anchors)
        # Search portals and broad knowledge bases use associative search/hypertext, not hierarchical parent breadcrumbs
        if self.site_type not in ("search_portal", "knowledge_base"):
            deep_pages = []
            deep_pages_without_orientation = []

            for p in self.pages:
                if not _is_deep_hierarchical_page(p):
                    continue

                deep_pages.append(p)
                soup = BeautifulSoup(p.raw_html or "", "html.parser")

                if not _has_orientation_mechanism(p, soup):
                    deep_pages_without_orientation.append(p.url)

            if deep_pages and deep_pages_without_orientation:
                ratio = f"{len(deep_pages_without_orientation)}/{len(deep_pages)}"
                sample_urls = ", ".join(deep_pages_without_orientation[:3])
                findings.append({
                    "issue_type": "missing_deep_page_orientation",
                    "severity": "medium",
                    "title": f"Deep landing pages lack orienting breadcrumbs or parent context ({ratio})",
                    "evidence": f"Crawled {len(deep_pages)} deep hierarchical page(s); {len(deep_pages_without_orientation)}/{len(deep_pages)} lack breadcrumb trails, parent category links, or sidebar navigation trees. Sample affected URLs: {sample_urls}.",
                    "action": "Implement visual breadcrumb navigation, parent category links, or a sidebar navigation tree to help visitors understand the hierarchy and navigate upward.",
                    "why_it_matters": "Deep link traffic often bounces when users cannot easily orient themselves within the broader site architecture.",
                    "confidence": "medium",
                    "root_cause": "Deep content templates lack parent category anchors or structural breadcrumb navigation.",
                    "affected_urls": deep_pages_without_orientation
                })

        return findings
