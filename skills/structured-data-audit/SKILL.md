---
name: structured-data-audit
description: Audits JSON-LD and Schema.org structured data, detecting missing Product/Offer schemas, Organization entities, syntax errors, and discrepancies between structured data and visible page text.
license: MIT
---

# Structured Data Audit (Semantic Web & Schema.org)

## When to use
Use this skill to determine whether a brand's website provides machine-readable semantic structured data that AI assistants (e.g. ChatGPT, Gemini, Perplexity) need to extract prices, products, business identity, and articles without ambiguity. Specifically detects:
- Missing `Product` and `Offer` JSON-LD markup on ecommerce / product detail pages.
- Missing `Organization` or `WebSite` schema on root brand pages.
- Malformed JSON syntax inside `<script type="application/ld+json">` tags that causes silent parsing failure.
- Incomplete schemas missing required properties (e.g., `price`, `priceCurrency`, `availability`).
- Discrepancies where the structured data price differs from the visible HTML text.

## Inputs
- `url` (string): The target website base URL or domain.
- `crawl_summary` (optional, object): Pre-fetched `CrawlSummary` containing parsed pages.

## Procedure
1. **JSON-LD Syntax Extraction**:
   - Extract all `<script type="application/ld+json">` blocks across sampled pages.
   - Parse each block using strict JSON decoding; capture exact syntax errors and line snippets.
2. **Page-Type Aware Schema Inspection**:
   - For **Product Pages**: Verify presence of schema.org `Product` with valid nested `Offer` (containing numeric price and ISO currency).
   - For **Homepage**: Verify presence of `Organization` or `LocalBusiness` declaring official brand name, URL, and entity properties.
   - For **Articles / Blogs**: Verify presence of `Article` with publication and author metadata.
   - Consult [required_schemas.md](file:///skills/structured-data-audit/references/required_schemas.md) for full property checklists.
3. **Consistency Verification**:
   - Compare structured data prices against visible text prices on the corresponding page to flag misleading or stale markup.
   - Consult [common_schema_errors.md](file:///skills/structured-data-audit/references/common_schema_errors.md) for severity grading.
4. **Evidence & Finding Construction**:
   - Emit evidence showing sample counts, exact URLs, and missing schema types.

## Output
Returns a structured list of findings conforming to the marketplace schema:
- `id`: e.g., `"SCHEMA-001"`
- `title`: Issue summary.
- `severity`: `"high"` | `"medium"` | `"critical"`.
- `evidence`: E.g. "Crawled 12 product pages; 0/12 contain schema.org markup."
- `suggested_action`: Actionable fix detailing exact schema properties to add or repair.

