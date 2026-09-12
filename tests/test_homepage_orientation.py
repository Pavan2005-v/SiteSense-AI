"""
Regression tests for context-aware homepage H1 / orientation detection (Phase 4).

Key invariants:
- Missing H1 alone is NEVER a high-severity defect.
- A homepage with no H1 but strong multi-signal orientation is NOT reported.
- A homepage with an H1 but poor purpose context IS reported (medium).
- Site-type contexts (search portal, docs, ecommerce, SaaS, blog, corporate)
  are evaluated by signals, not by title whitelists.
"""
import pytest
from bs4 import BeautifulSoup
from skills.common.models import PageData
from skills.engagement_audit.scripts.engagement_analyzer import EngagementAnalyzer
from tests.fixtures import (
    HOMEPAGE_NO_H1_EXCELLENT_ORIENTATION_HTML,
    PERFECT_HOMEPAGE_HTML,
)


def _page(html, url="https://example.com/", page_type="homepage", title="", meta_description="", **kwargs):
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return PageData(url=url, status_code=200, raw_html=html, text_content=text,
                    page_type=page_type, title=title or url, meta_description=meta_description, **kwargs)


def test_homepage_no_h1_excellent_orientation_not_reported():
    page = _page(
        HOMEPAGE_NO_H1_EXCELLENT_ORIENTATION_HTML,
        title="StreamDeck - Watch trailers, clips, and full episodes",
        meta_description="StreamDeck is a video streaming platform with thousands of movies, series, and creator clips. Browse trending trailers, build playlists, and subscribe to channels you love.",
    )
    issues = EngagementAnalyzer([page], site_type="other").audit_value_proposition_and_ctas()
    assert not any(i["issue_type"] in ("missing_h1_heading", "weak_homepage_purpose_clarity") for i in issues)


def test_homepage_h1_but_poor_purpose_clarity_reported():
    page = _page("<html><body><h1>Synergy</h1></body></html>", title="Synergy")
    issues = EngagementAnalyzer([page], site_type="other").audit_value_proposition_and_ctas()
    assert any(i["issue_type"] == "weak_homepage_purpose_clarity" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "weak_homepage_purpose_clarity")
    assert issue["severity"] in ("medium", "low")


def test_search_portal_homepage_without_h1_not_reported():
    # A search portal: search input + minimal text. site_type='search_portal' is exempt,
    # but even as 'other' the search utility + nav signals must prevent a false high.
    html = """<html><body>
        <form role="search" action="/search"><input type="search" name="q"></form>
        <nav><a href="/images">Images</a><a href="/news">News</a><a href="/maps">Maps</a></nav>
    </body></html>"""
    page = _page(html, title="QuickFind")
    analyzer = EngagementAnalyzer([page], site_type="search_portal")
    issues = analyzer.audit_value_proposition_and_ctas()
    assert not any(i["issue_type"] == "missing_h1_heading" for i in issues)
    analyzer2 = EngagementAnalyzer([page], site_type="other")
    issues2 = analyzer2.audit_value_proposition_and_ctas()
    assert not any(
        i["issue_type"] == "missing_h1_heading" and i["severity"] in ("high", "critical")
        for i in issues2
    )


def test_documentation_site_homepage_style_page_no_h1_no_false_positive():
    # Documentation homepage: nav, headings, body text — no H1, strong orientation.
    html = """<html><body>
        <header><nav><a href="/guide">Guide</a><a href="/api">API Reference</a><a href="/examples">Examples</a><a href="/cli">CLI</a></nav></header>
        <main>
            <h2>Build reliable data pipelines in minutes</h2>
            <h2>Connect any source, transform once, load anywhere</h2>
            <p>DataForge documentation covers installation, connectors, transformations, and deployment recipes for every supported runtime, with copy-paste examples throughout.</p>
        </main></body></html>"""
    page = _page(html, title="DataForge Documentation - Build reliable data pipelines", page_type="documentation")
    issues = EngagementAnalyzer([page], site_type="documentation").audit_value_proposition_and_ctas()
    h1_findings = [i for i in issues if i["issue_type"] == "missing_h1_heading"]
    assert not any(i["severity"] in ("high", "critical") for i in h1_findings)


def test_ecommerce_homepage_with_h1_and_cta_passes():
    page = _page(
        PERFECT_HOMEPAGE_HTML,
        title="AcmeCloud | Enterprise Cloud Management & Analytics Platform",
        meta_description="AcmeCloud provides automated enterprise cloud management, analytics, and security for global organizations.",
    )
    issues = EngagementAnalyzer([page], site_type="saas").audit_value_proposition_and_ctas()
    assert not any(i["issue_type"] in ("missing_h1_heading", "weak_homepage_purpose_clarity", "missing_clear_cta") for i in issues)


def test_blog_homepage_missing_h1_with_thin_signals_is_low_or_medium():
    # Thin personal blog homepage: title + a little text, no headings/nav/desc.
    html = """<html><body><p>Notes on running and software, updated occasionally.</p></body></html>"""
    page = _page(html, title="Runner's Notes")
    issues = EngagementAnalyzer([page], site_type="blog").audit_value_proposition_and_ctas()
    h1_findings = [i for i in issues if i["issue_type"] == "missing_h1_heading"]
    # Either not reported, or reported at low/medium — never high.
    assert all(i["severity"] in ("low", "medium") for i in h1_findings)


def test_generic_corporate_site_no_h1_but_nav_and_text_ok():
    html = """<html><body>
        <header><nav><a href="/services">Services</a><a href="/industries">Industries</a><a href="/careers">Careers</a><a href="/contact">Contact</a></nav></header>
        <main>
            <h2>Advisory services for growing companies</h2>
            <p>Meridian Advisory provides strategy, operations, and technology consulting to mid-market manufacturers and distributors across North America.</p>
        </main></body></html>"""
    page = _page(html, title="Meridian Advisory - Business consulting services", page_type="homepage")
    issues = EngagementAnalyzer([page], site_type="corporate").audit_value_proposition_and_ctas()
    assert not any(
        i["issue_type"] == "missing_h1_heading" and i["severity"] in ("high", "critical")
        for i in issues
    )
