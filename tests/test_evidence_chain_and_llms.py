"""
Test suite for evidence chain integrity, /llms.txt proactive handling,
limitations section, and human report formatting.
"""
import pytest
from skills.common.models import PageData, CrawlSummary, AuditFinding, SuggestedAction
from skills.audit_orchestrator.scripts.orchestrate import AuditOrchestrator
from skills.audit_orchestrator.scripts.report_builder import build_human_report
from tests.fixtures import PERFECT_HOMEPAGE_HTML


def test_missing_llms_txt_is_proactive_not_defect():
    # Site does not have llms.txt — must be emitted as is_proactive=True and not a critical/high defect
    p1 = PageData(
        url="https://acmecloud.io/",
        status_code=200,
        raw_html=PERFECT_HOMEPAGE_HTML,
        text_content="AcmeCloud Enterprise Cloud Management Next-Generation Cloud Orchestration",
        page_type="homepage"
    )
    summary = CrawlSummary(
        target_domain="acmecloud.io",
        start_url="https://acmecloud.io",
        crawled_at="2026-09-06T12:00:00Z",
        pages=[p1],
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /"
    )

    orchestrator = AuditOrchestrator("https://acmecloud.io")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    llms_findings = [f for f in report["findings"] if "/llms.txt" in f.get("title", "").lower()]
    assert len(llms_findings) == 1
    llms_f = llms_findings[0]
    assert llms_f.get("is_proactive") is True
    assert llms_f.get("recommendation_type") == "proactive"
    assert llms_f.get("severity") == "low"
    assert llms_f["suggested_action"]["priority"] == "low"
    assert "not mandatory" in llms_f.get("evidence", "").lower() or "optional" in llms_f.get("evidence", "").lower()


def test_affected_urls_integrity_and_deduplication():
    # Orchestrator cleans and validates affected_urls: no duplicates, matches target domain
    p1 = PageData(
        url="https://example.com/",
        status_code=200,
        raw_html="<html><body><h1>Home</h1></body></html>",
        page_type="homepage"
    )
    p2 = PageData(
        url="https://example.com/page-1",
        status_code=200,
        raw_html="<html><body><h1>Page 1</h1></body></html>",
        page_type="article"
    )
    test_finding = AuditFinding(
        id="",
        title="Test finding with sloppy URLs",
        severity="medium",
        evidence="Observed on test pages.",
        suggested_action=SuggestedAction(summary="Fix it", priority="medium"),
        affected_urls=[
            "https://example.com/page-1/",
            "https://example.com/page-1",
            "https://example.com/page-1#section",
            "https://unrelated-domain.org/hacked",
            ""
        ]
    )
    summary = CrawlSummary(
        target_domain="example.com",
        start_url="https://example.com",
        crawled_at="2026-09-06T12:00:00Z",
        pages=[p1, p2]
    )

    from unittest.mock import patch
    orchestrator = AuditOrchestrator("https://example.com")
    with patch("skills.audit_orchestrator.scripts.orchestrate.run_crawl_render_audit", return_value=[test_finding]), \
         patch("skills.audit_orchestrator.scripts.orchestrate.run_structured_data_audit", return_value=[]), \
         patch("skills.audit_orchestrator.scripts.orchestrate.run_freshness_corroboration_audit", return_value=[]), \
         patch("skills.audit_orchestrator.scripts.orchestrate.run_entity_clarity_audit", return_value=[]), \
         patch("skills.audit_orchestrator.scripts.orchestrate.run_engagement_audit", return_value=[]):
        report = orchestrator.run_full_audit(preloaded_summary=summary)

    target_f = next(f for f in report["findings"] if f["title"] == "Test finding with sloppy URLs")
    # All duplicate variations of /page-1 collapsed into one
    # Unrelated domain stripped
    # Empty string removed
    assert target_f["affected_urls"] == ["https://example.com/page-1"]


def test_limitations_and_human_report_generation():
    p1 = PageData(
        url="https://example.com/",
        status_code=200,
        raw_html="<html><body><h1>Example Site</h1></body></html>",
        page_type="homepage"
    )
    summary = CrawlSummary(
        target_domain="example.com",
        start_url="https://example.com",
        crawled_at="2026-09-06T12:00:00Z",
        pages=[p1],
        crawl_duration_seconds=3.2,
        site_type="corporate"
    )

    orchestrator = AuditOrchestrator("https://example.com")
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    # 1. Limitations section present
    assert "limitations" in report
    assert len(report["limitations"]) >= 2
    assert any("Bounded audit" in lim for lim in report["limitations"])
    assert any("Read-only" in lim for lim in report["limitations"])

    # 2. Audit metadata present
    assert "audit_metadata" in report
    assert report["audit_metadata"]["pages_crawled"] == 1
    assert report["audit_metadata"]["site_type"] == "corporate"

    # 3. Human report renders cleanly
    human_text = build_human_report(report)
    assert "BRAND AI-READINESS & ENGAGEMENT AUDIT" in human_text
    assert "EXECUTIVE SUMMARY" in human_text
    assert "AUDIT LIMITATIONS" in human_text
    assert "example.com" in human_text

