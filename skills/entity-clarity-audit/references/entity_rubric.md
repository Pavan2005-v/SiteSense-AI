# Entity Clarity and Disambiguation Rubric

## Overview
Large Language Models (LLMs) connect web mentions to real-world entities through Knowledge Graphs and lexical entity linking. When an entity has an ambiguous name (e.g., common English nouns like "Focus", "Canvas", "Apple", "Apex") without explicit disambiguating signals, AI assistants frequently confuse the brand with other businesses, dictionary definitions, or unrelated concepts.

## 1. The Entity Disambiguation Signals

### Authoritative Entity Anchors (`sameAs`)
- The `sameAs` array in schema.org `Organization` markup tells AI models exactly which knowledge base nodes represent this entity:
  - Wikidata URI (`https://www.wikidata.org/wiki/...`)
  - Official LinkedIn organization page
  - Crunchbase profile
  - Official Wikipedia / GitHub organization page
- **Missing `sameAs`**: Weakens knowledge graph grounding, making AI models rely on fragile unanchored string matching.
  - Severity: **Medium**

### Clear Brand + Sector Association in Meta Titles
- A title tag that says only `"Home"` or `"Welcome"` or `"Features"` provides zero brand entity association.
- Recommended pattern: `[Brand Name] | [Core Offering / Sector]`.
- Missing brand name in `<title>` across >50% of pages:
  - Severity: **High**

### Brand Name vs Common Noun Ambiguity
- When the inferred brand name is a single common English noun or dictionary word (<7 letters) and the homepage lacks:
  1. A clear high-level categorical descriptor (e.g. "cloud accounting software", "logistics provider").
  2. Clear physical or legal location details (e.g., incorporated in Delaware, based in San Francisco, CA).
- **Impact**: When users ask an AI assistant "What is [Brand]?", the AI will define the dictionary word or hallucinate a more famous namesake company.
  - Severity: **High**

### Contact & About Transparency
- Lack of an `/about` page or contact address weakens LLM confidence regarding legitimacy, often triggering "unverified organization" classification in retrieval systems.
  - Severity: **Medium**

