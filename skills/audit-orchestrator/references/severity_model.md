# Severity Model & Deterministic Rubric

## Principles of Severity Assignment
Severities are assigned deterministically based on **measurable mechanism impact**: does the defect completely blind AI retrieval engines, impair machine extraction confidence, introduce factual contradictions, or directly cause arriving visitors to bounce?

Severity is strictly separated from **Confidence**:
- **Severity**: The potential harm to discoverability or engagement if the condition holds.
- **Confidence**: The certainty and verifiability of the observation (High, Medium, Low).

---

## Severity Levels

### 1. Critical
- **Definition**: The defect completely blinds AI retrieval engines or search crawlers from accessing the brand, or renders core brand content completely absent in machine-readable representations.
- **Criteria**:
  - `User-agent: * Disallow: /` in `robots.txt` blocking the entire site.
  - `<meta name="robots" content="noindex">` on the root domain or primary public landing pages.
  - Empty SPA shell where the initial HTTP response has 0 readable content words for the entity (requiring full headless browser JS execution).
  - HTTP 5xx or persistent connection failure on canonical entry URLs.

### 2. High
- **Definition**: The content is reachable, but AI assistants cannot reliably extract facts, encounter contradictory claims, or human visitors cannot understand what is being offered or continue their journey.
- **Criteria**:
  - Missing `Product` and `Offer` JSON-LD on confirmed product detail pages (`product_detail`) on ecommerce sites.
  - Explicit blocking of major AI retrieval user-agents (`ChatGPT-User`, `PerplexityBot`, `Google-Extended`).
  - Core brand directories (`/products`, `/pricing`, `/about`) disallowed in `robots.txt`.
  - Conflicting pricing claims across internal pages (e.g., $19 on homepage vs $49 on pricing page).
  - Stale future roadmap commitments (e.g., "Launching in Q3 2022" when current year is 2026).
  - Malformed JSON-LD syntax causing complete schema discarding by search parsers.
  - Absence of any primary Call-To-Action (CTA) on high-intent conversion pages (`pricing`, `product_detail`, `service`).
  - Total lack of orientation on landing pages (no H1, H2, or title describing purpose).

### 3. Medium
- **Definition**: Causes friction, signals stale maintenance, leaves the entity ambiguous in knowledge graph lookups, or misses structured search opportunities.
- **Criteria**:
  - Copyright year out of date by $\ge 2$ years.
  - Missing `sameAs` authority links (Wikidata, LinkedIn) in Organization schema.
  - Generic or unbranded page titles across multiple pages (e.g. `<title>Home</title>`).
  - Deep landing pages ($\text{path depth} \ge 2$) lacking orienting breadcrumb navigation (excluding legal/privacy pages).
  - Informative content images lacking descriptive `alt` tags ($>40\%$ of images missing alt text).
  - Conflicting canonical targets or duplicate URL paths causing indexation ambiguity.
  - Proactive best-practice opportunities (`/llms.txt`, `FAQPage` schema).

---

## Non-Defects (Explicitly Suppressed to Prevent False Positives)
The following conditions MUST NOT be reported as defects:
1. **Absence of `robots.txt`**: The Adobe requirement is to *respect* robots.txt when present, not mandate its existence. A 404 on `robots.txt` means default crawlers are permitted.
2. **Missing sitemap in `robots.txt`**: Absence of a `Sitemap:` directive does not blind AI crawlers.
3. **Absence of `<h1>` alone**: If the page has clear purpose conveyed via `<title>`, `<h2>`, or prominent copy, absence of an explicit `<h1>` tag is not a high defect.
4. **No CTA on non-conversion pages**: Search engines, privacy policies, terms of service, documentation, and contact pages do not require commercial conversion CTAs.
5. **Few internal links on legal/policy pages**: Focused legal documents are intentionally self-contained and must not be flagged as "navigation dead ends".
6. **Missing canonical tag alone**: If there are no duplicate URL variants or parameter conflicts, absence of `<link rel="canonical">` is an observation, not a confirmed defect.
