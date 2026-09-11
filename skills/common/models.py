"""
Shared data models and types for Brand AI-Readiness & Engagement Audit.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


# --- Provenance / Observation ---

@dataclass
class Observation:
    """Internal provenance record linking an observation to its source."""
    url: str
    page_type: str
    observation: str
    evidence_snippet: str
    detection_method: str
    source_skill: str
    confidence: str = "high"  # "high", "medium", "low"


# --- Suggested Action ---

@dataclass
class SuggestedAction:
    summary: str
    priority: str  # "critical", "high", "medium", "low"
    implementation_guide: Optional[str] = None
    rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "summary": self.summary,
            "priority": self.priority
        }
        if self.implementation_guide:
            d["implementation_guide"] = self.implementation_guide
        if self.rationale:
            d["rationale"] = self.rationale
        return d


# --- Audit Finding ---

@dataclass
class AuditFinding:
    id: str
    title: str
    severity: str  # "critical", "high", "medium"
    evidence: str
    suggested_action: SuggestedAction
    category: Optional[str] = None
    confidence: str = "high"  # "high", "medium", "low" — separate from severity
    affected_urls: List[str] = field(default_factory=list)
    detection_method: Optional[str] = None
    is_proactive: bool = False
    why_it_matters: Optional[str] = None
    root_cause: Optional[str] = None
    observations: List[Observation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "suggested_action": self.suggested_action.to_dict()
        }
        if self.category:
            d["category"] = self.category
        if self.affected_urls:
            d["affected_urls"] = self.affected_urls
        if self.detection_method:
            d["detection_method"] = self.detection_method
        if self.is_proactive:
            d["is_proactive"] = True
            d["recommendation_type"] = "proactive"
        if self.why_it_matters:
            d["why_it_matters"] = self.why_it_matters
        if self.root_cause:
            d["root_cause"] = self.root_cause
        return d


# --- Page Data ---

@dataclass
class PageData:
    url: str
    status_code: int
    content_type: str = "text/html"
    raw_html: str = ""
    text_content: str = ""
    title: str = ""
    meta_description: str = ""
    meta_robots: str = ""
    canonical_url: Optional[str] = None
    h1_tags: List[str] = field(default_factory=list)
    h2_tags: List[str] = field(default_factory=list)
    internal_links: List[str] = field(default_factory=list)
    external_links: List[str] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    scripts: List[str] = field(default_factory=list)
    json_ld_raw: List[str] = field(default_factory=list)
    json_ld_parsed: List[Dict[str, Any]] = field(default_factory=list)
    page_type: str = "general"
    depth: int = 0
    fetch_error: Optional[str] = None
    response_headers: Dict[str, str] = field(default_factory=dict)


# --- Crawl Summary ---

@dataclass
class CrawlSummary:
    target_domain: str
    start_url: str
    crawled_at: str
    pages: List[PageData] = field(default_factory=list)
    robots_txt_found: bool = False
    robots_txt_content: str = ""
    disallowed_for_ai: List[str] = field(default_factory=list)
    sitemap_found: bool = False
    sitemap_urls: List[str] = field(default_factory=list)
    crawl_errors: List[Dict[str, str]] = field(default_factory=list)
    site_type: str = "other"  # ecommerce, corporate, saas, publisher, docs, portfolio, local_business, other
    crawl_duration_seconds: float = 0.0
    pages_skipped: int = 0
    robots_blocked_urls: List[str] = field(default_factory=list)
