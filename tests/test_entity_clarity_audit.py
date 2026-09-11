"""
Test suite for entity-clarity-audit skill.
"""
import pytest
from skills.common.models import PageData
from skills.entity_clarity_audit.scripts.disambiguation_rules import DisambiguationRules
from tests.fixtures import PERFECT_HOMEPAGE_HTML


def test_unbranded_titles_detected():
    p1 = PageData(
        url="https://genericbrand.io/",
        status_code=200,
        raw_html="<html><head><title>Home</title></head><body><h1>Welcome</h1></body></html>",
        title="Home",
        page_type="homepage"
    )
    p2 = PageData(
        url="https://genericbrand.io/pricing",
        status_code=200,
        raw_html="<html><head><title>Pricing</title></head><body><h1>Pricing</h1></body></html>",
        title="Pricing",
        page_type="pricing"
    )
    checker = DisambiguationRules([p1, p2], "genericbrand.io")
    issues = checker.audit_entity_clarity()

    assert any(i["issue_type"] == "unbranded_page_titles" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "unbranded_page_titles")
    assert issue["severity"] == "medium"


def test_common_dictionary_brand_collision_risk():
    p1 = PageData(
        url="https://apex.io/",
        status_code=200,
        raw_html="<html><head><title>Apex</title></head><body><h1>Welcome to Apex</h1></body></html>",
        title="Apex",
        page_type="homepage"
    )
    checker = DisambiguationRules([p1], "apex.io")
    issues = checker.audit_entity_clarity()

    assert any(i["issue_type"] == "brand_entity_collision_risk" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "brand_entity_collision_risk")
    assert issue["severity"] in ("medium", "high")
    assert "Apex" in issue["title"]


def test_perfect_entity_signals_pass():
    page = PageData(
        url="https://acmecloud.io/",
        status_code=200,
        raw_html=PERFECT_HOMEPAGE_HTML,
        title="AcmeCloud | Enterprise Cloud Management & Analytics Platform",
        page_type="homepage"
    )
    checker = DisambiguationRules([page], "acmecloud.io")
    issues = checker.audit_entity_clarity()
    assert not any(i["issue_type"] in ("unbranded_page_titles", "brand_entity_collision_risk") for i in issues)

