# Finding Deduplication & Root-Cause Clustering Rules

## Overview
When multiple specialist skills analyze the same website, they often observe different symptoms of the exact same root architectural defect. 
For example:
- `structured-data-audit` discovers that product pages have no `Product` JSON-LD.
- `crawl-render-audit` discovers that product specifications are rendered client-side only.

Emitting separate findings for these symptoms overwhelms the engineering team with disjointed reports. The `audit-orchestrator` merges overlapping findings into a single, high-leverage issue with consolidated evidence.

## Root-Cause Clusters

### 1. Entity Anchoring & Brand Disambiguation Cluster
- **Trigger**: Both `missing_org_schema` (from `structured-data-audit`) and `missing_authority_links` (from `entity-clarity-audit`) are flagged.
- **Resolution**: Merge into a single high-priority finding: `"Missing Organization Knowledge-Graph Schema and Authority Anchors"`.
- **Merged Evidence**: Combines the absence of JSON-LD schema with the lack of Wikidata/LinkedIn external references.
- **Consolidated Action**: "Add schema.org/Organization with complete 'sameAs' profile URLs to the root domain."

### 2. Product Machine-Readability & Schema Cluster
- **Trigger**: Both `missing_product_schema` and client-side render gaps on product detail pages.
- **Resolution**: Consolidate into `"Product details and pricing are not machine-readable in initial HTML"`.
- **Merged Evidence**: Documents both the lack of static text in the initial HTTP response and the absence of `Product` / `Offer` JSON-LD.
- **Consolidated Action**: "Implement SSR for product templates and embed schema.org/Product JSON-LD with valid offer pricing."

### 3. Page Title & Brand Association Cluster
- **Trigger**: Both `missing_h1_heading` on homepage and `unbranded_page_titles`.
- **Resolution**: Keep highest-severity item and attach secondary context in evidence details.

## Deduplication Strategy
1. Group findings by target URL or entity scope.
2. Check for cluster signature keywords in issue titles / categories.
3. If two findings share >= 70% semantic scope, merge them:
   - Inherit the highest severity (`critical` > `high` > `medium`).
   - Concatenate evidence into a unified proof string.
   - Synthesize a comprehensive action that fixes both issues simultaneously.

