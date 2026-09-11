---
name: crawl-render-audit
description: Audits website crawlability, robots.txt directives for AI user-agents, canonical tags, noindex signals, and JavaScript rendering gaps where content is invisible to machine readers.
license: MIT
---

# Crawl & Render Audit (Discoverability & Machine Ingestion)

## When to use
Use this skill when diagnosing whether an AI assistant or web crawler is prevented from accessing, reading, or indexing a brand's website. Specifically identifies:
- Explicit disallows or blocks against AI search agents (e.g. `GPTBot`, `ChatGPT-User`, `PerplexityBot`, `ClaudeBot`).
- Total crawler lockouts (`User-agent: * Disallow: /`).
- Empty client-rendered SPA shells where initial HTML lacks substantive text.
- Critical facts trapped inside non-text graphics or images without alt descriptions.
- Accidental `noindex` directives or missing canonical links on public landing pages.

## Inputs
- `url` (string): The target website base URL or domain (e.g., `https://example.com`).
- `crawl_summary` (optional, object): Pre-fetched `CrawlSummary` containing raw HTML and metadata.
- `max_pages` (optional, integer): Maximum pages to inspect (default: 15).

## Procedure
1. **Robots Directive Analysis**:
   - Fetch `/robots.txt`.
   - Parse rules for general crawlers (`*`) and dedicated AI agents (`GPTBot`, `ChatGPT-User`, `ClaudeBot`, `Google-Extended`, `PerplexityBot`).
   - Flag any full-site disallow, AI-specific exclusion, or disallow on core directories (`/products`, `/about`, `/pricing`).
   - Consult [crawl_rules.md](file:///skills/crawl-render-audit/references/crawl_rules.md) for severity thresholds.

2. **Bounded Polite Crawl**:
   - Crawl up to `max_pages` using BFS prioritization (Homepage > About > Products/Services > Pricing > Contact).
   - Enforce a 6-second per-request timeout and read-only HTTP GET requests.

3. **Render Gap & Machine-Readability Verification**:
   - Compare raw HTML structure against extracted text content.
   - Flag SPA root containers (`#root`, `#app`) returning under 50 words in initial HTML.
   - Detect non-text locking: identify informative images lacking descriptive `alt` text.
   - Inspect meta tags for `<meta name="robots" content="noindex">` or missing `<link rel="canonical">`.
   - Consult [render_gap_heuristics.md](file:///skills/crawl-render-audit/references/render_gap_heuristics.md) for evaluation criteria.

4. **Evidence Formulation & Finding Construction**:
   - Format each issue with concrete evidence (exact URLs, status codes, word counts, blocked user-agents).
   - Assign deterministic severity (`critical`, `high`, `medium`).
   - Generate actionable fix guidance detailing what to change and why.

## Output
Returns a structured list of findings conforming to the marketplace schema:
- `id`: e.g., `"CRAWL-001"`
- `title`: Concise issue description.
- `severity`: `"critical"` | `"high"` | `"medium"`.
- `evidence`: Concrete numerical / text proof.
- `suggested_action`: Actionable fix with `summary` and `priority`.

