"""
Test suite for freshness-corroboration skill.
"""
import pytest
from skills.common.models import PageData
from skills.freshness_corroboration.scripts.corroboration_checker import CorroborationChecker
from tests.fixtures import (
    STALE_CONFLICTING_HOMEPAGE_HTML,
    STALE_CONFLICTING_PRICING_HTML,
    PERFECT_HOMEPAGE_HTML
)


def test_stale_copyright_and_roadmap_detected():
    page = PageData(
        url="https://legacysoft.example/",
        status_code=200,
        raw_html=STALE_CONFLICTING_HOMEPAGE_HTML,
        text_content="LegacySoft Business Automation Plans starting at $19 per month. Roadmap 2022: We are launching our cloud edition in Q3 2022! Copyright 2021",
        page_type="homepage"
    )
    checker = CorroborationChecker([page])
    issues = checker.audit_freshness_and_consistency()

    assert any(i["issue_type"] == "stale_copyright" for i in issues)
    copyright_issue = next(i for i in issues if i["issue_type"] == "stale_copyright")
    assert copyright_issue["severity"] == "medium"
    assert "2021" in copyright_issue["evidence"]

    assert any(i["issue_type"] == "stale_roadmap" for i in issues)
    roadmap_issue = next(i for i in issues if i["issue_type"] == "stale_roadmap")
    assert roadmap_issue["severity"] == "high"


def test_cross_page_pricing_contradiction_detected():
    p1 = PageData(
        url="https://legacysoft.example/",
        status_code=200,
        raw_html=STALE_CONFLICTING_HOMEPAGE_HTML,
        text_content="Plans starting at $19 per month",
        page_type="homepage"
    )
    p2 = PageData(
        url="https://legacysoft.example/pricing",
        status_code=200,
        raw_html=STALE_CONFLICTING_PRICING_HTML,
        text_content="Plans from $49 per month for full platform access",
        page_type="pricing"
    )
    checker = CorroborationChecker([p1, p2])
    issues = checker.audit_freshness_and_consistency()

    assert any(i["issue_type"] == "conflicting_pricing_claims" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "conflicting_pricing_claims")
    assert issue["severity"] == "high"
    assert "$19" in issue["evidence"]
    assert "$49" in issue["evidence"]


def test_fresh_site_passes_cleanly():
    page = PageData(
        url="https://acmecloud.io/",
        status_code=200,
        raw_html=PERFECT_HOMEPAGE_HTML,
        text_content="AcmeCloud Enterprise Cloud Management Copyright 2026",
        page_type="homepage"
    )
    checker = CorroborationChecker([page])
    issues = checker.audit_freshness_and_consistency()
    assert not any(i["issue_type"] in ("stale_copyright", "stale_roadmap", "conflicting_pricing_claims") for i in issues)

