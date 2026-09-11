---
name: engagement-audit
description: Audits on-site visitor retention, above-the-fold value proposition clarity, navigation dead ends, deep-page orientation, and call-to-action friction that cause arriving visitors to bounce.
license: MIT
---

# On-Site Engagement & Visitor Retention Audit

## When to use
Use this skill to determine why human visitors arriving on a website (including those referred by AI assistant citations) fail to understand the brand, navigate deeper, or convert. Specifically audits:
- Above-the-fold value proposition clarity: Missing or empty `<h1>` headings, or abstract corporate buzzwords lacking clear product utility.
- Navigation dead ends: Deep content or informational pages that offer 0-1 internal links or no next steps.
- Deep-page disorientation: Visitors landing on subpages via AI search queries who find no breadcrumbs or parent category anchors to orient themselves.
- Call-to-action (CTA) friction: Conversion and product pages missing clear, high-contrast action buttons.

## Inputs
- `url` (string): The target website base URL or domain.
- `crawl_summary` (optional, object): Pre-fetched `CrawlSummary` containing parsed pages.

## Procedure
1. **Value Proposition & Heading Analysis**:
   - Inspect the homepage heading hierarchy.
   - Flag missing `<h1>` tags or multiple competing `<h1>` elements.
   - Detect empty slogans or vague buzzwords without explanatory subheadings.
2. **Call-to-Action (CTA) Verification**:
   - Scan key landing pages (homepage, product, pricing, service) for explicit conversion action buttons (e.g. "Get Started", "Request Demo", "Buy Now").
3. **Internal Navigation & Dead-End Graphing**:
   - Traverse the internal link graph of crawled pages.
   - Identify content pages with 0 or 1 outbound links.
   - Check if deep pages (depth >= 2) provide breadcrumb orientation trails or parent links.
   - Consult [engagement_heuristics.md](file:///skills/engagement-audit/references/engagement_heuristics.md) for scoring rules.
4. **Evidence & Finding Construction**:
   - Document the exact URLs, missing CTA buttons, and dead-end paths.
   - Provide concrete recommendations for layout improvements, headline revisions, and navigation pathways.

## Output
Returns a structured list of findings conforming to the marketplace schema:
- `id`: e.g., `"ENGAGE-001"`
- `title`: Concise issue description.
- `severity`: `"high"` | `"medium"`.
- `evidence`: E.g. "Conversion pages lack explicit next-step buttons: https://...".
- `suggested_action`: Actionable fix detailing how to improve orientation and visitor engagement.

