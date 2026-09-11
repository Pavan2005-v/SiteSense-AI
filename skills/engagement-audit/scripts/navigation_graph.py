"""
Analyzes site navigation architecture, deep-page orientation, and dead-end pathways.
"""
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from skills.common.page_classifier import is_legal_page


class NavigationGraph:
    def __init__(self, pages: List[Any]):
        self.pages = pages

    def audit_navigation_and_orientation(self) -> List[Dict[str, Any]]:
        findings = []

        # 1. Dead-End Pages Check
        # Require genuinely 0 internal links (not just <=1)
        dead_end_pages = []
        dead_end_core_pages = []
        
        for p in self.pages:
            if p.page_type == "homepage":
                continue
            if is_legal_page(p.page_type) or p.page_type == "documentation":
                continue
                
            if len(p.internal_links) == 0:
                dead_end_pages.append(p.url)
                if p.page_type in ["homepage", "product_detail", "pricing", "service"]:
                    dead_end_core_pages.append(p.url)

        if dead_end_core_pages:
            findings.append({
                "issue_type": "navigation_dead_ends",
                "severity": "high",
                "title": f"Navigation dead-end detected on {len(dead_end_core_pages)} core page(s)",
                "evidence": f"Core pages contain zero internal links, trapping visitors without next navigation steps.",
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
                "evidence": f"Pages contain zero internal links, trapping visitors without next navigation steps.",
                "action": "Add related content links or persistent footer navigation to ensure visitors can explore deeper without bouncing.",
                "why_it_matters": "When secondary pages lack navigation, visitors who arrived via search or external links are likely to bounce.",
                "confidence": "high",
                "root_cause": "Orphaned pages or missing global navigation templates.",
                "affected_urls": non_core_dead_ends
            })

        # 2. Deep-Page Orientation & Context Retention
        deep_pages = []
        deep_pages_without_breadcrumbs = []

        for p in self.pages:
            if is_legal_page(p.page_type):
                continue
                
            parsed = urlparse(p.url)
            path_segments = [s for s in parsed.path.split("/") if s]
            if len(path_segments) >= 2:
                deep_pages.append(p)
                soup = BeautifulSoup(p.raw_html, "html.parser")
                
                # Check for breadcrumb signals
                has_breadcrumb_nav = bool(
                    soup.find("nav", attrs={"aria-label": lambda x: x and "breadcrumb" in x.lower()}) or
                    soup.find(class_=lambda x: x and "breadcrumb" in x.lower()) or
                    soup.find(id=lambda x: x and "breadcrumb" in x.lower())
                )
                has_breadcrumb_schema = "breadcrumblist" in (p.raw_html or "").lower()

                if not (has_breadcrumb_nav or has_breadcrumb_schema):
                    deep_pages_without_breadcrumbs.append(p.url)

        if deep_pages and deep_pages_without_breadcrumbs:
            ratio = f"{len(deep_pages_without_breadcrumbs)}/{len(deep_pages)}"
            findings.append({
                "issue_type": "missing_deep_page_orientation",
                "severity": "medium",
                "title": f"Deep landing pages lack orienting breadcrumbs or parent context ({ratio})",
                "evidence": f"Visitors landing directly on deep URLs lack breadcrumbs or category context.",
                "action": "Implement visual breadcrumb navigation and BreadcrumbList JSON-LD to help visitors understand the hierarchy and navigate up to parent categories.",
                "why_it_matters": "Deep link traffic often bounces when users cannot easily orient themselves within the broader site architecture.",
                "confidence": "medium",
                "root_cause": "Missing breadcrumb component on sub-category or article page templates.",
                "affected_urls": deep_pages_without_breadcrumbs
            })

        return findings
