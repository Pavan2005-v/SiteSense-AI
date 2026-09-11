"""
Test suite for orchestrator deduplication and synthesis logic.
"""
import pytest
from skills.common.models import AuditFinding, SuggestedAction
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

