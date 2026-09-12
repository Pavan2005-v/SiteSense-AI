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
    # Bare homepage with no H1 and NO alternative orientation signals.
    # Corrected behavior (Phase 4): missing H1 alone must never be a high-severity
    # defect; a defect requires evidence of an actual orientation failure. With zero
    # orientation signals the finding is medium, not high.
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
    assert issue["severity"] == "medium"


def test_missing_h1_with_excellent_orientation_is_not_reported():
    # Homepage with no H1 but strong orientation (title, meta description, headings,
    # navigation, body text, actions) must NOT be flagged (Phase 4).
    page = PageData(
        url="https://example.com/",
        status_code=200,
        title="StreamFlix - Unlimited Movies, Shows, and Live TV",
        meta_description="Watch thousands of movies, award-winning shows, and live sports on StreamFlix. Start your free trial today and cancel anytime.",
        raw_html="""<html><head><title>StreamFlix - Unlimited Movies, Shows, and Live TV</title></head><body>
            <header><nav><a href='/movies'>Movies</a><a href='/shows'>Shows</a><a href='/live'>Live TV</a><a href='/signup'>Sign Up</a></nav></header>
            <main>
                <h2>Unlimited streaming, one simple subscription</h2>
                <h2>Watch on any device, anywhere</h2>
                <p>StreamFlix gives you instant access to thousands of movies and shows with new titles added every week. Download episodes for offline viewing and create up to five personalized profiles for your household.</p>
                <a class='btn' href='/signup'>Start Free Trial</a>
            </main></body></html>""",
        text_content="StreamFlix Unlimited streaming, one simple subscription Watch on any device, anywhere StreamFlix gives you instant access to thousands of movies and shows with new titles added every week. Download episodes for offline viewing and create up to five personalized profiles for your household. Start Free Trial",
        page_type="homepage"
    )
    analyzer = EngagementAnalyzer([page])
    issues = analyzer.audit_value_proposition_and_ctas()

    assert not any(i["issue_type"] in ("missing_h1_heading", "weak_homepage_purpose_clarity") for i in issues)


def test_h1_but_poor_purpose_clarity_is_reported():
    # Homepage with an H1 but essentially no other purpose context -> reported, medium.
    page = PageData(
        url="https://example.com/",
        status_code=200,
        raw_html="<html><body><h1>Synergy</h1></body></html>",
        page_type="homepage"
    )
    analyzer = EngagementAnalyzer([page])
    issues = analyzer.audit_value_proposition_and_ctas()

    assert any(i["issue_type"] == "weak_homepage_purpose_clarity" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "weak_homepage_purpose_clarity")
    assert issue["severity"] in ("medium", "low")


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

