"""
Test suite for engagement-audit skill.
"""
import pytest
from skills.common.models import PageData
from skills.engagement_audit.scripts.engagement_analyzer import EngagementAnalyzer
from skills.engagement_audit.scripts.navigation_graph import NavigationGraph
from tests.fixtures import (
    DEAD_END_DEEP_PAGE_HTML,
    PERFECT_HOMEPAGE_HTML
)


def test_missing_h1_on_homepage():
    page = PageData(
        url="https://example.com/",
        status_code=200,
        raw_html="<html><body><p>Some text without any H1</p></body></html>",
        page_type="homepage"
    )
    analyzer = EngagementAnalyzer([page])
    issues = analyzer.audit_value_proposition_and_ctas()

    assert any(i["issue_type"] == "missing_h1_heading" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "missing_h1_heading")
    assert issue["severity"] == "high"


def test_missing_cta_on_conversion_page():
    page = PageData(
        url="https://example.com/pricing",
        status_code=200,
        raw_html="<html><body><h1>Pricing</h1><p>Our prices are affordable.</p></body></html>",
        page_type="pricing"
    )
    analyzer = EngagementAnalyzer([page])
    issues = analyzer.audit_value_proposition_and_ctas()

    assert any(i["issue_type"] == "missing_clear_cta" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "missing_clear_cta")
    assert issue["severity"] == "high"


def test_navigation_dead_ends_detected():
    page = PageData(
        url="https://example.com/blog/deep-guide",
        status_code=200,
        raw_html=DEAD_END_DEEP_PAGE_HTML,
        page_type="article",
        internal_links=[]
    )
    graph = NavigationGraph([page])
    issues = graph.audit_navigation_and_orientation()

    assert any(i["issue_type"] == "navigation_dead_ends" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "navigation_dead_ends")
    assert issue["severity"] in ("medium", "high")


def test_deep_page_missing_breadcrumbs():
    p1 = PageData(
        url="https://example.com/docs/api/v2",
        status_code=200,
        raw_html="<html><body><h1>API V2</h1><a href='/'>Home</a><a href='/docs'>Docs</a></body></html>",
        page_type="documentation",
        internal_links=["https://example.com/", "https://example.com/docs"]
    )
    graph = NavigationGraph([p1])
    issues = graph.audit_navigation_and_orientation()

    assert any(i["issue_type"] == "missing_deep_page_orientation" for i in issues)


def test_perfect_site_engagement_passes():
    page = PageData(
        url="https://acmecloud.io/",
        status_code=200,
        raw_html=PERFECT_HOMEPAGE_HTML,
        page_type="homepage",
        internal_links=["https://acmecloud.io/products", "https://acmecloud.io/pricing"]
    )
    analyzer = EngagementAnalyzer([page])
    issues = analyzer.audit_value_proposition_and_ctas()
    assert not any(i["issue_type"] in ("missing_h1_heading", "missing_clear_cta") for i in issues)

