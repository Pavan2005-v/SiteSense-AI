"""
Test suite for orchestrator deduplication and synthesis logic.
"""
import pytest
from skills.common.models import AuditFinding, SuggestedAction, CrawlSummary, PageData
from skills.audit_orchestrator.scripts.orchestrate import deduplicate_findings


def test_entity_schema_and_authority_merging():
    # Simulate overlapping findings from structured-data and entity-clarity
    f1 = AuditFinding(
        id="SCHEMA-001",
        title="Homepage lacks Organization structured data",
        severity="medium",
        evidence="Homepage does not declare schema.org/Organization",
        suggested_action=SuggestedAction(summary="Add Organization JSON-LD", priority="medium"),
        category="structured-data"
    )
    f2 = AuditFinding(
        id="ENTITY-001",
        title="No authoritative entity profile links (Wikidata, LinkedIn)",
        severity="medium",
        evidence="No verified external organization profile links found",
        suggested_action=SuggestedAction(summary="Link Wikidata & LinkedIn profiles", priority="medium"),
        category="entity-clarity"
    )

    merged = deduplicate_findings([f1, f2])

    assert len(merged) == 1, f"Expected 1 consolidated finding, got {len(merged)}"
    consolidated = merged[0]
    assert consolidated.severity == "high"
    assert "Missing Organization Knowledge-Graph" in consolidated.title
    assert "schema.org/Organization" in consolidated.evidence
    assert "Wikidata" in consolidated.evidence


def test_proactive_recommendations_do_not_inflate_severity_counts():
    """
    Phase 15/23: summary.critical/high/medium/low count DEFECTS only. Proactive
    recommendations are tracked separately and never inflate defect severity counts.
    """
    from skills.audit_orchestrator.scripts.report_builder import build_final_report, validate_report_schema

    defect = AuditFinding(
        id="", title="Sample defect", severity="medium", confidence="high",
        evidence="Observed evidence.", category="engagement",
        suggested_action=SuggestedAction(summary="Fix it", priority="medium"),
        affected_urls=["https://example.com/"]
    )
    proactive = AuditFinding(
        id="", title="Proactive: optional enhancement", severity="medium", confidence="medium",
        evidence="Contextual opportunity.", category="discoverability",
        suggested_action=SuggestedAction(summary="Consider it", priority="low"),
        affected_urls=["https://example.com/"], is_proactive=True, recommendation_type="proactive"
    )
    summary = CrawlSummary(
        target_domain="example.com", start_url="https://example.com",
        crawled_at="2026-09-12T00:00:00Z",
        pages=[PageData(url="https://example.com/", status_code=200, page_type="homepage")]
    )
    report = build_final_report(site="example.com", findings=[defect, proactive], crawl_summary=summary)

    assert report["summary"]["medium"] == 1          # defects only
    assert report["summary"]["total_defects"] == 1
    assert report["summary"]["total_proactive"] == 1
    assert report["summary"]["total_findings"] == 2
    assert validate_report_schema(report) is True

