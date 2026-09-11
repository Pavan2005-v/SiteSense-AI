---
name: audit-orchestrator
description: Designated entrypoint skill for Brand AI-Readiness and On-Site Engagement Audits. Coordinates specialist skills, deduplicates overlapping findings, normalizes severity, synthesizes proactive recommendations, and emits the final report conforming to the Adobe specification.
license: MIT
---

# Brand AI-Readiness & Engagement Audit Orchestrator

## When to use
Use this entrypoint skill to conduct an end-to-end audit of any brand website or domain. Evaluates both:
1. **Off-site / AI Discoverability**: Why AI assistants (ChatGPT, Gemini, Claude, Perplexity) cannot find, parse, corroborate, or cite brand offerings.
2. **On-site Engagement**: Why visitors arriving on the website fail to understand the value proposition, encounter navigation dead ends, or fail to engage.

Produces a single, deterministic, evidence-backed report with prioritized suggested actions and proactive enhancements.

## Inputs
- `url` (string, required): Target website base URL or domain (e.g. `https://example.com`).
- `max_pages` (integer, optional): Maximum pages to inspect during bounded crawl (default: 12).
- `preloaded_summary` (object, optional): Pre-existing `CrawlSummary` object for offline testing or pre-crawled fixtures.

## Procedure
1. **Initialize Bounded Polite Crawl**:
   - Verify input target and initialize read-only HTTP session.
   - Fetch `/robots.txt` and check AI crawler permissions.
   - Crawl up to `max_pages` using BFS priority queue (Homepage > About > Products > Pricing > Contact).
2. **Execute Specialist Skills**:
   - Invoke `crawl-render-audit` to detect robots blocks, canonicalization errors, and JavaScript rendering gaps.
   - Invoke `structured-data-audit` to validate schema.org markup (`Product`, `Offer`, `Organization`, syntax errors).
   - Invoke `freshness-corroboration` to detect stale copyright, outdated roadmaps, and cross-page factual conflicts.
   - Invoke `entity-clarity-audit` to detect brand disambiguation risks and unanchored knowledge graph entities.
   - Invoke `engagement-audit` to evaluate above-the-fold value proposition, conversion CTAs, and navigation dead ends.
3. **Deduplicate & Cluster Root Causes**:
   - Merge overlapping findings across skills according to [deduplication_rules.md](file:///skills/audit-orchestrator/references/deduplication_rules.md).
4. **Normalize Severity & Prioritize Actions**:
   - Apply deterministic severity levels (`critical`, `high`, `medium`) per [severity_model.md](file:///skills/audit-orchestrator/references/severity_model.md).
   - Score and prioritize suggested actions per [prioritization_matrix.md](file:///skills/audit-orchestrator/references/prioritization_matrix.md).
5. **Inject Proactive Recommendations**:
   - Evaluate eligibility for proactive enhancements (e.g., `/llms.txt`, `FAQPage` schema) per [proactive_catalog.md](file:///skills/audit-orchestrator/references/proactive_catalog.md).
6. **Emit Strict Adobe JSON Report**:
   - Build output matching Adobe required schema and validate with `validate_report_schema()`.

## Output
Returns a structured JSON document conforming to the Adobe Round 3 specification:
```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": {
    "total_findings": 6,
    "critical": 1,
    "high": 2,
    "medium": 3
  },
  "findings": [
    {
      "id": "F-001",
      "title": "No JSON-LD structured data on product pages",
      "severity": "high",
      "evidence": "Crawled 12 product pages; 0/12 contain schema.org markup.",
      "suggested_action": {
        "summary": "Add Product/Offer JSON-LD to every product page.",
        "priority": "high"
      }
    }
  ]
}
```
Consult [architecture.md](file:///skills/audit-orchestrator/references/architecture.md) for full composition flow details.

