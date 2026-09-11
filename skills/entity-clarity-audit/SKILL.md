---
name: entity-clarity-audit
description: Audits brand entity disambiguation, unbranded page titles, missing sameAs authority links, and entity confusion risks where common noun brand names cause AI assistants to mix up or misrepresent the brand.
license: MIT
---

# Entity Clarity & Brand Disambiguation Audit

## When to use
Use this skill when auditing why an AI assistant confuses a brand with dictionary words, unrelated companies, or cannot identify what the organization does. Specifically detects:
- Brand name collision risk when using common dictionary nouns (e.g. "Apex", "Canvas", "Focus") without sector qualification.
- Unbranded or generic page titles (e.g. `<title>Home</title>` or `<title>Pricing</title>`) that strip entity context from AI web snippets.
- Missing authoritative entity links (`sameAs` profiles linking to Wikidata, LinkedIn, or Crunchbase).
- Shallow homepage copy lacking an explicit, machine-extractable mission statement or categorical definition.

## Inputs
- `url` (string): The target website base URL or domain.
- `crawl_summary` (optional, object): Pre-fetched `CrawlSummary` containing parsed pages.

## Procedure
1. **Entity Extraction**:
   - Extract candidate brand names from the domain, `og:site_name`, and JSON-LD markup.
   - Scan page links and schema blocks for authoritative profile links (Wikidata, Wikipedia, LinkedIn, Crunchbase).
2. **Disambiguation Analysis**:
   - Evaluate title tags across sampled pages: flag pages that omit the brand name.
   - Check if the brand name matches high-risk ambiguous dictionary terms without qualifying sector keywords.
   - Inspect the homepage for clear descriptive copy explaining who the company is and what it provides.
   - Consult [entity_rubric.md](file:///skills/entity-clarity-audit/references/entity_rubric.md) for severity grading rules.
3. **Evidence & Finding Construction**:
   - Detail the exact unbranded page titles, missing profile anchors, and collision vectors.
   - Formulate actionable recommendations to disambiguate the brand across metadata and knowledge graph schemas.

## Output
Returns a structured list of findings conforming to the marketplace schema:
- `id`: e.g., `"ENTITY-001"`
- `title`: Summary of the entity ambiguity issue.
- `severity`: `"high"` | `"medium"`.
- `evidence`: E.g. "Page titles lack brand name anchors in <title>, causing entity attribution loss."
- `suggested_action`: Actionable fix detailing how to anchor brand identity and disambiguate names.

