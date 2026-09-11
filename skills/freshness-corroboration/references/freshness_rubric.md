# Freshness & Corroboration Evaluation Rubric

## Overview
AI assistants (e.g. ChatGPT, Gemini, Claude, Perplexity) frequently evaluate the temporal freshness and corroboration of claims before citing them as reliable answers.
If a website presents contradictory dates, outdated pricing, expired roadmaps, or uncorroborated claims, AI models lower their confidence score or produce disclaimer warnings (e.g., "According to 2021 records...").

## 1. Temporal Signals & Staleness Rules

### Copyright Notice Age
- The footer copyright year serves as a general freshness pulse for web crawlers.
- **Stale Threshold**: Copyright year older than 2 years prior to the current audit year (e.g., Copyright 2021-2023 when the current year is 2026).
  - Severity: **Medium**
  - Mechanism: Causes automated crawlers to treat the entire domain as unmaintained.

### Stale Roadmaps / Time-Sensitive Offerings
- Landing pages advertising "Upcoming in 2022" or "Q3 2023 Beta" that are still live without updates.
  - Severity: **High**
  - Mechanism: AI assistants quote historical roadmaps as current, leading to misrepresentation and user complaints.

### Missing Publication / Modified Dates on Informational Content
- Core articles, whitepapers, or documentation pages lacking `dateModified` or `datePublished`.
  - Severity: **Medium**

## 2. Cross-Page Contradictions
When different pages on the same domain state conflicting facts:
- **Pricing Contradictions**: Homepage says "Starting at $19/mo", Pricing page says "Starting at $29/mo".
  - Severity: **High**
- **Company Fact Contradictions**: "Founded in 2018" vs "Founded in 2015".
  - Severity: **Medium**

## 3. Claim Corroboration & Fragility
AI assistants prefer citing claims that are backed by independent references, certificates, customer case studies, or explicit source citations.
- **Fragile Assertion**: Superlative claims like "The #1 Rated Platform", "100% Guaranteed", "Over 500,000 active users" that are presented as naked marketing text without any source, survey date, audit badge, or citation link.
  - Severity: **Medium**
  - Suggested Action: Add verifiable citation markers (e.g. "G2 Grid Leader Winter 2025" with link, or audited customer metric date).

