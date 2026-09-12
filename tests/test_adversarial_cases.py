"""
Adversarial test cases designed to expose false positives and verify generalization.
"""
import pytest
from skills.common.models import PageData, CrawlSummary
from skills.structured_data_audit.scripts.schema_validator import SchemaValidator
from skills.entity_clarity_audit.scripts.disambiguation_rules import DisambiguationRules
from skills.engagement_audit.scripts.engagement_analyzer import EngagementAnalyzer
from skills.audit_orchestrator.scripts.orchestrate import AuditOrchestrator
from tests.fixtures import PERFECT_HOMEPAGE_HTML


def test_no_product_schema_penalty_on_non_product_site():
    # A corporate consulting firm with no products should NEVER be penalized for lacking Product schema
    page = PageData(
        url="https://consulting.example/about",
        status_code=200,
        raw_html="<html><body><h1>About Global Advisory</h1><p>Strategic management consulting.</p></body></html>",
        text_content="About Global Advisory Strategic management consulting",
        page_type="about"
    )
    validator = SchemaValidator([page])
    issues = validator.audit_all_pages()

    assert not any(i["issue_type"] == "missing_product_schema" for i in issues)


def test_common_word_with_strong_sector_clarity_not_flagged():
    # Brand is 'Focus', a common word, but the title clearly disambiguates: 'Focus Enterprise CRM & Marketing'
    page = PageData(
        url="https://focuscrm.io/",
        status_code=200,
        raw_html="<html><head><title>Focus Enterprise CRM &amp; Marketing Automation Platform</title></head><body><h1>Enterprise CRM Platform</h1></body></html>",
        title="Focus Enterprise CRM & Marketing Automation Platform",
        page_type="homepage"
    )
    rules = DisambiguationRules([page], "focuscrm.io")
    issues = rules.audit_entity_clarity()

    assert not any(i["issue_type"] == "brand_entity_collision_risk" for i in issues)


def test_end_to_end_on_perfect_site_has_zero_critical_or_high_defects():
    # Running the full audit orchestrator on an exemplary site should produce 0 critical and 0 high defects
    p1 = PageData(
        url="https://acmecloud.io/",
        status_code=200,
        raw_html=PERFECT_HOMEPAGE_HTML,
        text_content="AcmeCloud Enterprise Cloud Management Next-Generation Cloud Orchestration for High-Growth Engineering Teams AcmeCloud automates multicloud infrastructure governance, cost optimization, and compliance monitoring across AWS, Azure, and Google Cloud. Start Free Trial Request Demo Copyright 2026 AcmeCloud Technologies Inc.",
        title="AcmeCloud | Enterprise Cloud Management & Analytics Platform",
        meta_description="Enterprise cloud management and infrastructure analytics.",
        page_type="homepage",
        internal_links=["https://acmecloud.io/docs", "https://acmecloud.io/pricing"]
    )
    p2 = PageData(
        url="https://acmecloud.io/docs",
        status_code=200,
        raw_html="<html><head><title>AcmeCloud Documentation | Multi-Cloud Guide</title></head><body><nav><a href='/'>Home</a> <a href='/pricing'>Pricing</a></nav><h1>AcmeCloud Documentation</h1><p>Comprehensive multicloud infrastructure governance and analytics modules guide for engineering teams.</p></body></html>",
        text_content="AcmeCloud Documentation | Multi-Cloud Guide Comprehensive multicloud infrastructure governance and analytics modules guide for engineering teams.",
        page_type="documentation",
        internal_links=["https://acmecloud.io/", "https://acmecloud.io/pricing"]
    )
    p3 = PageData(
        url="https://acmecloud.io/pricing",
        status_code=200,
        raw_html="<html><head><title>AcmeCloud Pricing | Enterprise Subscription Plans</title></head><body><nav><a href='/'>Home</a> <a href='/docs'>Docs</a></nav><h1>Subscription Plans</h1><p>Transparent enterprise tiers with annual billing discounts for organizations.</p><a href='/signup'>Start Free Trial</a></body></html>",
        text_content="AcmeCloud Pricing | Enterprise Subscription Plans Transparent enterprise tiers with annual billing discounts for organizations. Start Free Trial",
        page_type="pricing",
        internal_links=["https://acmecloud.io/", "https://acmecloud.io/docs"]
    )
    summary = CrawlSummary(
        target_domain="acmecloud.io",
        start_url="https://acmecloud.io",
        crawled_at="2026-09-06T12:00:00Z",
        pages=[p1, p2, p3],
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /\nSitemap: https://acmecloud.io/sitemap.xml",
        site_type="saas"
    )

    orchestrator = AuditOrchestrator("https://acmecloud.io")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    # All findings must be 0 critical, 0 high (only proactive medium recommendations permitted)
    assert report["summary"]["critical"] == 0, [f["title"] for f in report["findings"]]
    assert report["summary"]["high"] == 0, [f["title"] for f in report["findings"]]
    assert report["summary"]["total_findings"] > 0
    # Proactive recommendations are present
    assert any("Proactive" in f["title"] for f in report["findings"])


def test_intentional_noindex_on_legal_and_privacy_pages_not_reported_as_defect():
    # Privacy policy and terms pages frequently and legitimately use noindex directives.
    # They must NOT be flagged as discoverability defects.
    from skills.crawl_render_audit.scripts.render_comparator import RenderComparator

    privacy_page = PageData(
        url="https://example.com/privacy",
        status_code=200,
        raw_html="<html><head><meta name='robots' content='noindex, nofollow'></head><body><h1>Privacy Policy</h1><p>Legal terms...</p></body></html>",
        meta_robots="noindex, nofollow",
        page_type="legal"
    )
    terms_page = PageData(
        url="https://example.com/terms-of-service",
        status_code=200,
        raw_html="<html><head><meta name='robots' content='noindex'></head><body><h1>Terms of Service</h1><p>Agreements...</p></body></html>",
        meta_robots="noindex",
        page_type="legal"
    )
    comparator = RenderComparator([privacy_page, terms_page])
    issues = comparator.audit_render_gaps()

    # No defect findings should be produced for intentional legal noindex
    assert not any(i["issue_type"] == "meta_noindex_detected" for i in issues)


def test_search_portal_homepage_exempt_from_commercial_cta_and_h1_defects():
    # A search portal (e.g. Google or internal search tool) has search utility intent,
    # not a SaaS/e-commerce signup funnel. It should not be flagged for missing commercial CTA or H1.
    search_home = PageData(
        url="https://searchengine.example/",
        status_code=200,
        title="SearchEngine — Fast Web Search",
        raw_html="""
        <html>
        <head><title>SearchEngine</title></head>
        <body>
          <form action="/search">
            <input type="text" name="q" placeholder="Search the web" />
            <input type="submit" value="SearchEngine Search" />
            <button type="submit">I'm Feeling Lucky</button>
          </form>
        </body>
        </html>
        """,
        text_content="SearchEngine Search I'm Feeling Lucky",
        page_type="homepage"
    )

    analyzer = EngagementAnalyzer([search_home], site_type="search_portal")
    issues = analyzer.audit_value_proposition_and_ctas()

    # Search portal with clear search input and submit buttons must not flag missing CTA or missing H1
    assert not any(i["issue_type"] == "missing_clear_cta" for i in issues)
    assert not any(i["issue_type"] == "missing_h1_heading" for i in issues)


def test_title_count_synchronization_with_affected_urls():
    from skills.audit_orchestrator.scripts.orchestrate import sync_title_page_count, AuditFinding, SuggestedAction

    # 1. Direct regex synchronization
    assert sync_title_page_count("Missing H1 heading on 1 page(s)", 3) == "Missing H1 heading on 3 page(s)"
    assert sync_title_page_count("No clear primary Call-To-Action on 2 conversion page(s)", 1) == "No clear primary Call-To-Action on 1 conversion page(s)"
    assert sync_title_page_count("Unbranded page titles on 5 pages", 2) == "Unbranded page titles on 2 page(s)"
    # Non-counting titles remain unchanged
    assert sync_title_page_count("Missing Organization Knowledge-Graph schema", 1) == "Missing Organization Knowledge-Graph schema"


def test_robots_wildcard_blocks_all_crawlers_without_duplicate_ai_finding():
    """Wildcard crawl block (User-agent: * Disallow: /) must produce 1 Critical defect, not duplicate AI defect."""
    from skills.crawl_render_audit.scripts.robots_checker import RobotsChecker

    checker = RobotsChecker("https://chatgpt.example", "User-agent: *\nDisallow: /\n")
    issues = checker.audit_ai_access()

    assert len(issues) == 1
    assert issues[0]["issue_type"] == "all_crawlers_blocked"
    assert issues[0]["severity"] == "critical"
    # No duplicate ai_crawlers_blocked defect when wildcard block already subsumes it
    assert not any(i["issue_type"] == "ai_crawlers_blocked" for i in issues)


def test_identifiable_entity_without_wikidata_has_no_defect():
    """An identifiable company with descriptive title and copyright must NOT receive a defect for lacking Wikidata/LinkedIn."""
    p1 = PageData(
        url="https://innovativetech.example/",
        status_code=200,
        raw_html="<html><head><title>InnovativeTech — Enterprise Workflow Automation Platform</title></head><body><h1>Enterprise Automation</h1><p>About our company. Founded in 2021.</p><footer><p>© 2026 InnovativeTech Inc.</p><a href='/about'>About Us</a></footer></body></html>",
        title="InnovativeTech — Enterprise Workflow Automation Platform",
        text_content="Enterprise Automation About our company. Founded in 2021. © 2026 InnovativeTech Inc. About Us",
        page_type="homepage",
        internal_links=["https://innovativetech.example/about"]
    )
    rules = DisambiguationRules([p1], "innovativetech.example", site_type="saas")
    issues = rules.audit_entity_clarity()

    # Must produce 0 defects for missing Wikidata/LinkedIn/Crunchbase
    assert not any(i["issue_type"] == "missing_authority_links" for i in issues)


def test_zero_page_robots_blocked_audit_reports_honest_coverage_and_unknown_site():
    """When 0 pages can be inspected, site_type is unknown, engagement checks_run is 0, and limitations are clear."""
    summary = CrawlSummary(
        target_domain="blocked.example.com",
        start_url="https://blocked.example.com",
        crawled_at="2026-09-12T12:00:00Z",
        site_type="unknown",
        pages=[],
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nDisallow: /\n",
        robots_blocked_urls=["https://blocked.example.com"]
    )
    orchestrator = AuditOrchestrator("https://blocked.example.com")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    # Site classification remains unknown (does not guess from domain)
    assert report["audit_metadata"]["site_type"] == "unknown"
    # Coverage honesty: 0 engagement checks run because 0 pages could be inspected
    assert report["coverage"]["engagement"]["checks_run"] == 0
    assert report["coverage"]["discoverability"]["checks_run"] == 1  # Only robots.txt inspected
    # Limitation explains zero pages inspected
    assert any("zero pages crawled" in lim.lower() for lim in report["limitations"])


def test_ssrf_redirect_protection():
    """SSRF checker correctly rejects loopback, private, and metadata IP targets."""
    from skills.common.url_utils import is_safe_url

    assert is_safe_url("http://127.0.0.1") is False
    assert is_safe_url("http://localhost:8080") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_url("http://10.0.0.1/admin") is False
    assert is_safe_url("http://192.168.1.1") is False
    assert is_safe_url("http://metadata.google.internal") is False
    assert is_safe_url("https://example.com/page") is True
    assert is_safe_url("https://sub.domain.co.uk/path?q=1") is True

