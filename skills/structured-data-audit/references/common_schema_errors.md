# Common Structured Data Errors and Severity Model

## Error Categories & Severity Rules

### 1. Missing Core Schema on Inferred Page Type
- **Product Page lacking `Product` / `Offer`**:
  - Severity: **High**
  - Rationale: The Adobe problem statement specifically highlights missing Product/Offer JSON-LD as a primary discoverability defect. Without it, conversational shopping agents and price comparison LLMs cannot ground product pricing or availability.
- **Homepage lacking `Organization` or `WebSite`**:
  - Severity: **High**
  - Rationale: Prevents automated knowledge graph builders from linking the domain to an authoritative entity.
- **Article Page lacking `Article` / `datePublished`**:
  - Severity: **Medium**

### 2. Syntax & Parsing Errors in JSON-LD
- **Malformed JSON**:
  - Unquoted keys, trailing commas, unescaped quotes, or bad character encodings inside `<script type="application/ld+json">`.
  - Severity: **High**
  - Rationale: Entire JSON-LD block is silently discarded by parsers, completely nullifying any embedded metadata.

### 3. Missing Mandatory Sub-Properties
- `Product` missing `name` or `image`: **Medium**
- `Offer` missing `price` or `priceCurrency`: **High**
- `Article` missing `datePublished`: **Medium**
- `Organization` missing `name` or `url`: **Medium**

### 4. Semantic Discrepancy (Visible Content vs Structured Data)
- Declared schema price differs from text price on page (e.g. schema says $19.99, visible HTML says $29.99).
  - Severity: **High**
  - Rationale: Triggers spam penalties and causes hallucinated answers in AI assistants.

### 5. False Positive Guards
- Do **not** penalize a B2B SaaS marketing page for lacking `Product` or `LocalBusiness` schema.
- Do **not** penalize a 2-page portfolio for lacking `BreadcrumbList`.
- Always adapt requirements to the inferred page type.

