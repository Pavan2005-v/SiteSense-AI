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
        internal_links=["https://acmecloud.io/products", "https://acmecloud.io/pricing"]
    )
    summary = CrawlSummary(
        target_domain="acmecloud.io",
        start_url="https://acmecloud.io",
        crawled_at="2026-09-06T12:00:00Z",
        pages=[p1],
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /\nSitemap: https://acmecloud.io/sitemap.xml"
    )

    orchestrator = AuditOrchestrator("https://acmecloud.io")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    # All findings must be 0 critical, 0 high (only proactive medium recommendations permitted)
    assert report["summary"]["critical"] == 0
    assert report["summary"]["high"] == 0
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

