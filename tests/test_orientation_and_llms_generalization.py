"""
Regression test suite for generic deep-page orientation, site-type awareness,
and conditional /llms.txt proactive recommendation logic.
Verifies that fixes generalize across diverse site archetypes without domain-specific hardcoding.
"""
import pytest
from skills.common.models import PageData, CrawlSummary
from skills.common.page_classifier import classify_page, get_effective_path_depth
from skills.engagement_audit.scripts.navigation_graph import (
    NavigationGraph,
    _is_deep_hierarchical_page,
    _has_orientation_mechanism
)
from skills.audit_orchestrator.scripts.orchestrate import AuditOrchestrator
from bs4 import BeautifulSoup


# ==============================================================================
# 1. KNOWLEDGE-BASE ARCHETYPE
# ==============================================================================

def test_knowledge_base_orientation_exempt():
    """Knowledge bases are associative webs of hypertext, exempt from rigid parent breadcrumbs."""
    p_main = PageData(
        url="https://wiki.example.org/wiki/Main_Page",
        status_code=200,
        raw_html="<html><body><h1>Main Page</h1><p>Welcome to the encyclopedia.</p><a href='/wiki/Physics'>Physics</a></body></html>",
        page_type="homepage",
        title="Main Page - Wiki",
        h1_tags=["Main Page"],
        internal_links=["https://wiki.example.org/wiki/Physics"]
    )
    p_article = PageData(
        url="https://wiki.example.org/wiki/Physics",
        status_code=200,
        raw_html="""<html><body>
            <h1>Physics</h1>
            <p>Physics is the natural science of matter.</p>
            <div id='catlinks'><a href='/wiki/Category:Natural_sciences'>Natural sciences</a></div>
            <a href='/wiki/Main_Page'>Main Page</a>
        </body></html>""",
        page_type="article",
        title="Physics - Wiki",
        h1_tags=["Physics"],
        internal_links=["https://wiki.example.org/wiki/Main_Page"]
    )

    graph = NavigationGraph([p_main, p_article], site_type="knowledge_base")
    issues = graph.audit_navigation_and_orientation()

    # Knowledge bases must NOT produce missing_deep_page_orientation defects
    assert not any(i["issue_type"] == "missing_deep_page_orientation" for i in issues)


# ==============================================================================
# 2. DOCUMENTATION ARCHETYPE
# ==============================================================================

def test_documentation_site_hierarchical_breadcrumbs():
    """Documentation sites with deep articles require orienting mechanisms (breadcrumbs or sidebar)."""
    # Page with sidebar tree -> oriented
    p_with_sidebar = PageData(
        url="https://docs.example.io/guides/getting-started/installation",
        status_code=200,
        raw_html="""<html><body>
            <nav class="sidebar">
                <a href="/guides">Guides</a>
                <a href="/guides/getting-started">Getting Started</a>
                <a href="/guides/getting-started/installation">Installation</a>
            </nav>
            <h1>Installation</h1>
        </body></html>""",
        page_type="documentation"
    )
    soup_oriented = BeautifulSoup(p_with_sidebar.raw_html, "html.parser")
    assert _has_orientation_mechanism(p_with_sidebar, soup_oriented) is True

    # Page with NO orientation -> defect
    p_unoriented = PageData(
        url="https://docs.example.io/guides/getting-started/configuration",
        status_code=200,
        raw_html="<html><body><h1>Configuration</h1><p>Set up your env.</p></body></html>",
        page_type="documentation"
    )
    soup_unoriented = BeautifulSoup(p_unoriented.raw_html, "html.parser")
    assert _has_orientation_mechanism(p_unoriented, soup_unoriented) is False

    graph = NavigationGraph([p_with_sidebar, p_unoriented], site_type="documentation")
    issues = graph.audit_navigation_and_orientation()

    assert any(i["issue_type"] == "missing_deep_page_orientation" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "missing_deep_page_orientation")
    assert issue["affected_urls"] == ["https://docs.example.io/guides/getting-started/configuration"]


# ==============================================================================
# 3. E-COMMERCE ARCHETYPE
# ==============================================================================

def test_ecommerce_deep_catalog_orientation():
    """Deep product detail pages in e-commerce catalogs require parent category orientation."""
    # Deep product with visual breadcrumbs
    p_oriented = PageData(
        url="https://store.example.com/shop/footwear/running/shoe-alpha",
        status_code=200,
        raw_html="""<html><body>
            <nav aria-label="breadcrumb">
                <a href="/shop">Shop</a> &gt; <a href="/shop/footwear">Footwear</a> &gt; <span>Shoe Alpha</span>
            </nav>
            <h1>Shoe Alpha</h1>
        </body></html>""",
        page_type="product_detail"
    )
    # Deep product missing breadcrumbs and parent links
    p_disoriented = PageData(
        url="https://store.example.com/shop/footwear/running/shoe-beta",
        status_code=200,
        raw_html="<html><body><h1>Shoe Beta</h1><p>$120 - Buy now</p></body></html>",
        page_type="product_detail"
    )

    graph = NavigationGraph([p_oriented, p_disoriented], site_type="ecommerce")
    issues = graph.audit_navigation_and_orientation()

    assert any(i["issue_type"] == "missing_deep_page_orientation" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "missing_deep_page_orientation")
    # Affected URLs must only contain the unoriented page, never the oriented one
    assert issue["affected_urls"] == ["https://store.example.com/shop/footwear/running/shoe-beta"]


# ==============================================================================
# 4. CORPORATE / MARKETING FLAT ARCHETYPE
# ==============================================================================

def test_corporate_marketing_flat_site_no_breadcrumb_penalty():
    """Flat corporate and marketing pages do not require breadcrumb trails."""
    pages = [
        PageData(url="https://corp.example.com/", status_code=200, raw_html="<h1>Corp</h1>", page_type="homepage"),
        PageData(url="https://corp.example.com/about", status_code=200, raw_html="<h1>About</h1>", page_type="about"),
        PageData(url="https://corp.example.com/services", status_code=200, raw_html="<h1>Services</h1>", page_type="service"),
        PageData(url="https://corp.example.com/contact", status_code=200, raw_html="<h1>Contact</h1>", page_type="contact"),
    ]
    graph = NavigationGraph(pages, site_type="corporate")
    issues = graph.audit_navigation_and_orientation()

    # Zero deep pages exist; no orientation defect may be emitted
    assert not any(i["issue_type"] == "missing_deep_page_orientation" for i in issues)


# ==============================================================================
# 5. PORTALS AND ROOT PAGES ARE NEVER CLASSIFIED AS DEEP
# ==============================================================================

def test_portal_and_language_pages_not_deep():
    """Portals, language main pages, and root directories are not deep pages."""
    p1 = PageData(url="https://example.org/wiki/Main_Page", status_code=200, page_type="homepage", title="Main Page")
    p2 = PageData(url="https://example.org/en/", status_code=200, page_type="homepage", title="Home")
    p3 = PageData(url="https://example.org/portal", status_code=200, page_type="homepage", title="Welcome Portal")
    p4 = PageData(url="https://example.org/fr/accueil_principal", status_code=200, page_type="homepage", title="Accueil")

    for p in (p1, p2, p3, p4):
        assert _is_deep_hierarchical_page(p) is False

    # Effective path depth checks
    assert get_effective_path_depth("https://example.org/") == 0
    assert get_effective_path_depth("https://example.org/wiki/Main_Page") == 0
    assert get_effective_path_depth("https://example.org/en/about") == 1
    assert get_effective_path_depth("https://example.org/docs/api/v2") == 3


# ==============================================================================
# 6. CONDITIONAL /llms.txt PROACTIVE RECOMMENDATION
# ==============================================================================

def test_llms_txt_suppressed_for_search_portals():
    """Search portals do not serve static documentation and must not receive /llms.txt recommendation."""
    summary = CrawlSummary(
        target_domain="search.example.com",
        start_url="https://search.example.com",
        crawled_at="2026-09-12T12:00:00Z",
        site_type="search_portal",
        pages=[PageData(url="https://search.example.com", status_code=200, page_type="search")]
    )
    orchestrator = AuditOrchestrator("https://search.example.com")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    assert not any("/llms.txt" in f.get("title", "").lower() for f in report["findings"])


def test_llms_txt_suppressed_for_knowledge_bases():
    """Knowledge bases rely on structured data APIs and must not be spammed with /llms.txt."""
    summary = CrawlSummary(
        target_domain="wiki.example.org",
        start_url="https://wiki.example.org",
        crawled_at="2026-09-12T12:00:00Z",
        site_type="knowledge_base",
        pages=[
            PageData(url="https://wiki.example.org/wiki/Main_Page", status_code=200, page_type="homepage"),
            PageData(url="https://wiki.example.org/wiki/Article_1", status_code=200, page_type="article"),
            PageData(url="https://wiki.example.org/wiki/Article_2", status_code=200, page_type="article"),
        ]
    )
    orchestrator = AuditOrchestrator("https://wiki.example.org")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    assert not any("/llms.txt" in f.get("title", "").lower() for f in report["findings"])


def test_llms_txt_suppressed_for_single_page_stub():
    """Minimal single-page sites have no documentation corpus to summarize."""
    summary = CrawlSummary(
        target_domain="simple.example.com",
        start_url="https://simple.example.com",
        crawled_at="2026-09-12T12:00:00Z",
        site_type="other",
        pages=[PageData(url="https://simple.example.com/", status_code=200, page_type="homepage")]
    )
    orchestrator = AuditOrchestrator("https://simple.example.com")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    assert not any("/llms.txt" in f.get("title", "").lower() for f in report["findings"])


def test_llms_txt_recommended_for_rich_documentation_or_saas():
    """Multi-page documentation or SaaS platforms genuinely benefit from /llms.txt."""
    summary = CrawlSummary(
        target_domain="api.example.io",
        start_url="https://api.example.io",
        crawled_at="2026-09-12T12:00:00Z",
        site_type="documentation",
        pages=[
            PageData(url="https://api.example.io/", status_code=200, page_type="homepage"),
            PageData(url="https://api.example.io/docs/quickstart", status_code=200, page_type="documentation"),
            PageData(url="https://api.example.io/docs/auth", status_code=200, page_type="documentation"),
        ]
    )
    orchestrator = AuditOrchestrator("https://api.example.io")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    llms_f = next((f for f in report["findings"] if "/llms.txt" in f.get("title", "").lower()), None)
    assert llms_f is not None
    assert llms_f["is_proactive"] is True
    assert llms_f["severity"] == "low"
    assert "optional" in llms_f["evidence"].lower() or "emerging" in llms_f["evidence"].lower()
