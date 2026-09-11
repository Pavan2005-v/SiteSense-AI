---
name: freshness-corroboration
description: Audits temporal signals, stale copyright dates, expired roadmaps, cross-page factual contradictions, and fragile uncorroborated claims that hurt AI trust and citation reliability.
license: MIT
---

# Freshness & Corroboration Audit

## When to use
Use this skill when auditing why an AI assistant perceives a brand as stale, unmaintained, or untrustworthy. Identifies:
- Outdated footer copyright notices (>= 2 years behind current year) that signal lack of maintenance to automated scrapers.
- Expired future roadmaps or time-sensitive claims left un-updated.
- Cross-page factual conflicts (such as divergent pricing claims between the homepage and pricing table).
- High-stakes superlative claims (e.g. "#1 platform") published with zero third-party corroboration or source methodology.

## Inputs
- `url` (string): The target website base URL or domain.
- `crawl_summary` (optional, object): Pre-fetched `CrawlSummary` containing parsed pages.

## Procedure
1. **Temporal Extraction**:
   - Parse footer text and `<time>` tags to identify the most recent copyright and publication dates.
   - Scan body text for historical years framed as active future roadmaps (e.g. "Roadmap 2022").
2. **Cross-Page Consistency Checking**:
   - Compare pricing tiers, figures, and company milestones stated across the homepage, pricing pages, and product pages.
   - Flag any divergence in pricing or core offerings across internal pages.
3. **Corroboration & Citation Fragility**:
   - Identify superlative marketing claims and inspect the page DOM for authoritative citation markers or external links.
   - Consult [freshness_rubric.md](file:///skills/freshness-corroboration/references/freshness_rubric.md) for severity grading.
4. **Evidence & Finding Construction**:
   - Document the contradictory phrases, exact URLs, and observed dates.
   - Formulate prioritized fixes that synchronize facts and add verifiable citation anchors.

## Output
Returns a structured list of findings conforming to the marketplace schema:
- `id`: e.g., `"FRESH-001"`
- `title`: Summary of staleness or contradiction.
- `severity`: `"high"` | `"medium"`.
- `evidence`: E.g. "Copyright notices across sampled pages display 2022 (current year: 2026)."
- `suggested_action`: Actionable fix detailing how to synchronize dates and claims.

