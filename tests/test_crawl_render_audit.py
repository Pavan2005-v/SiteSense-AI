"""
Test suite for crawl-render-audit skill.
"""
import pytest
from skills.common.models import PageData, CrawlSummary
from skills.crawl_render_audit.scripts.robots_checker import RobotsChecker
from skills.crawl_render_audit.scripts.render_comparator import RenderComparator
from skills.crawl_render_audit.scripts.audit_crawl import run_crawl_render_audit
from tests.fixtures import SPA_EMPTY_SHELL_HTML, PERFECT_HOMEPAGE_HTML


def test_robots_ai_agents_blocked():
    robots_txt = """
    User-agent: *
    Allow: /

    User-agent: GPTBot
    Disallow: /

    User-agent: ChatGPT-User
    Disallow: /
    """
    checker = RobotsChecker("https://example.com", robots_txt)
    issues = checker.audit_ai_access()
    
    assert any(i["issue_type"] == "ai_crawlers_blocked" for i in issues)
    ai_issue = next(i for i in issues if i["issue_type"] == "ai_crawlers_blocked")
    assert ai_issue["severity"] == "high"
    assert "GPTBot" in ai_issue["evidence"]


def test_robots_wildcard_blocked():
    robots_txt = """
    User-agent: *
    Disallow: /
    """
    checker = RobotsChecker("https://example.com", robots_txt)
    issues = checker.audit_ai_access()
    assert any(i["issue_type"] == "all_crawlers_blocked" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "all_crawlers_blocked")
    assert issue["severity"] == "critical"


def test_render_gap_detected_on_empty_spa():
    page = PageData(
        url="https://example.com/app",
        status_code=200,
        raw_html=SPA_EMPTY_SHELL_HTML,
        text_content="Modern SPA Portal",
        page_type="homepage"
    )
    comparator = RenderComparator([page])
    issues = comparator.audit_render_gaps()
    
    assert any(i["issue_type"] == "js_render_gap" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "js_render_gap")
    assert issue["severity"] in ("critical", "high")
    assert "empty SPA mount container" in issue["evidence"]


def test_render_comparator_clean_on_perfect_site():
    page = PageData(
        url="https://acmecloud.io/",
        status_code=200,
        raw_html=PERFECT_HOMEPAGE_HTML,
        text_content="Next-Generation Cloud Orchestration for High-Growth Engineering Teams",
        page_type="homepage"
    )
    comparator = RenderComparator([page])
    issues = comparator.audit_render_gaps()
    assert not any(i["issue_type"] == "js_render_gap" for i in issues)

