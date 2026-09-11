"""
Test suite for context-aware canonical analysis and confidence-gating rules.
"""
import pytest
from skills.common.models import PageData, AuditFinding, SuggestedAction, CrawlSummary
from skills.crawl_render_audit.scripts.render_comparator import RenderComparator
from skills.audit_orchestrator.scripts.orchestrate import AuditOrchestrator


def test_missing_canonical_alone_produces_no_defect():
    # Site has unique pages, no duplicates, but simply omits <link rel="canonical">
    p1 = PageData(
        url="https://example.com/",
        status_code=200,
        raw_html="<html><body><h1>Home</h1><p>Unique content A</p></body></html>",
        text_content="Unique content A",
        canonical_url=None
    )
    p2 = PageData(
        url="https://example.com/about",
        status_code=200,
        raw_html="<html><body><h1>About</h1><p>Unique content B</p></body></html>",
        text_content="Unique content B",
        canonical_url=None
    )
    comparator = RenderComparator([p1, p2])
    issues = comparator.audit_render_gaps()

    # Missing canonical alone should NOT be a defect
    assert not any(i.get("issue_type") == "missing_canonical_tags" for i in issues)


def test_duplicate_pages_without_canonical_triggers_finding():
    # Two distinct URLs with near-identical content and no canonical resolution
    content = "Detailed specifications for Enterprise Cloud Gateway Model X500."
    p1 = PageData(
        url="https://example.com/products/x500",
        status_code=200,
        raw_html=f"<html><body><h1>Product X500</h1><p>{content}</p></body></html>",
        text_content=content,
        canonical_url=None
    )
    p2 = PageData(
        url="https://example.com/items/x500?ref=promo",
        status_code=200,
        raw_html=f"<html><body><h1>Product X500</h1><p>{content}</p></body></html>",
        text_content=content,
        canonical_url=None
    )
    comparator = RenderComparator([p1, p2])
    issues = comparator.audit_render_gaps()

    assert any(i.get("issue_type") == "unresolved_duplicate_content" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "unresolved_duplicate_content")
    assert issue["severity"] in ("medium", "high")
    assert "duplicate" in issue["evidence"].lower()


def test_conflicting_canonical_target_triggers_finding():
    # Page declares a canonical pointing to a completely different domain or page
    p1 = PageData(
        url="https://example.com/page-a",
        status_code=200,
        raw_html="<html><head><link rel='canonical' href='https://example.com/page-b'></head><body><p>Content</p></body></html>",
        text_content="Content",
        canonical_url="https://example.com/page-b"
    )
    comparator = RenderComparator([p1])
    issues = comparator.audit_render_gaps()

    assert any(i.get("issue_type") == "conflicting_canonical" for i in issues)


def test_low_confidence_cannot_become_critical_or_high():
    # Simulate an orchestrator run where an issue has confidence='low'
    low_conf_finding = AuditFinding(
        id="",
        title="Uncorroborated marketing statement",
        severity="high",  # Erroneously labeled high
        confidence="low",  # But confidence is low!
        evidence="Soft heuristic triggered without proof.",
        suggested_action=SuggestedAction(summary="Review text", priority="low"),
        category="freshness",
        affected_urls=["https://example.com/"]
    )
    summary = CrawlSummary(
        target_domain="example.com",
        start_url="https://example.com",
        crawled_at="2026-09-06T12:00:00Z",
        pages=[PageData(url="https://example.com/", status_code=200)]
    )

    orchestrator = AuditOrchestrator("https://example.com")
    # Patch specialist outputs to inject this test finding
    from unittest.mock import patch
    with patch("skills.audit_orchestrator.scripts.orchestrate.run_crawl_render_audit", return_value=[low_conf_finding]), \
         patch("skills.audit_orchestrator.scripts.orchestrate.run_structured_data_audit", return_value=[]), \
         patch("skills.audit_orchestrator.scripts.orchestrate.run_freshness_corroboration_audit", return_value=[]), \
         patch("skills.audit_orchestrator.scripts.orchestrate.run_entity_clarity_audit", return_value=[]), \
         patch("skills.audit_orchestrator.scripts.orchestrate.run_engagement_audit", return_value=[]):
        report = orchestrator.run_full_audit(preloaded_summary=summary)

    # Must have been downgraded from high to medium by confidence gating!
    matching = [f for f in report["findings"] if f["title"] == "Uncorroborated marketing statement"]
    assert len(matching) == 1
    assert matching[0]["severity"] == "medium"

