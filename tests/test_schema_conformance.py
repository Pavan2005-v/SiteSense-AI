"""
Test suite validating conformance to the Adobe Round 3 sample audit report schema.
"""
import pytest
from skills.common.models import AuditFinding, SuggestedAction
from skills.audit_orchestrator.scripts.report_builder import build_final_report, validate_report_schema


def test_adobe_sample_schema_conformance():
    findings = [
        AuditFinding(
            id="F-001",
            title="No JSON-LD structured data on product pages",
            severity="high",
            evidence="Crawled 12 product pages; 0/12 contain schema.org markup.",
            suggested_action=SuggestedAction(
                summary="Add Product/Offer JSON-LD to every product page.",
                priority="high"
            )
        ),
        AuditFinding(
            id="F-002",
            title="All crawlers completely blocked in robots.txt",
            severity="critical",
            evidence="robots.txt contains User-agent: * Disallow: /.",
            suggested_action=SuggestedAction(
                summary="Allow search and AI crawlers to access public brand pages.",
                priority="critical"
            )
        ),
        AuditFinding(
            id="F-003",
            title="Stale copyright notice",
            severity="medium",
            evidence="Copyright notice displays 2021.",
            suggested_action=SuggestedAction(
                summary="Update copyright notice to 2026.",
                priority="medium"
            )
        )
    ]

    report = build_final_report("example.com", findings, "2026-09-20T14:32:00Z")

    # 1. Validate required top-level fields
    assert report["site"] == "example.com"
    assert report["audited_at"] == "2026-09-20T14:32:00Z"
    assert "summary" in report
    assert "findings" in report

    # 2. Validate summary counts
    assert report["summary"]["total_findings"] == 3
    assert report["summary"]["critical"] == 1
    assert report["summary"]["high"] == 1
    assert report["summary"]["medium"] == 1

    # 3. Validate finding structure
    f0 = report["findings"][0]
    assert f0["id"] == "F-001"
    assert f0["title"] == "No JSON-LD structured data on product pages"
    assert f0["severity"] == "high"
    assert f0["evidence"] == "Crawled 12 product pages; 0/12 contain schema.org markup."
    assert f0["suggested_action"]["summary"] == "Add Product/Offer JSON-LD to every product page."
    assert f0["suggested_action"]["priority"] == "high"

    # 4. Strict jsonschema validation
    assert validate_report_schema(report) is True

