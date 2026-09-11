# Brand AI-Readiness & On-Site Engagement Audit Marketplace
**Adobe University Hackathon 2026 — Round 3 Submission**

[![agentskills.io compliant](https://img.shields.io/badge/spec-agentskills.io-blue.svg)](https://agentskills.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 39 Passed](https://img.shields.io/badge/tests-39%20passed-brightgreen.svg)]()
[![Runtime: < 60s](https://img.shields.io/badge/runtime-%3C%2060s%20bounded-blue.svg)]()

A general-purpose, deterministic **Agent Skill Marketplace** that automatically audits any website or domain for both **Off-Site / AI Discoverability** (why the brand is invisible, stale, or misrepresented in AI assistants like ChatGPT, Gemini, Claude, and Perplexity) and **On-Site Visitor Engagement** (why human visitors arriving on the website fail to understand, navigate, retain context, or convert).

Emits a single structured audit report conforming strictly to the official **Adobe Round 3 sample audit report schema**, providing concrete evidence, deterministic severities, prioritized actionable fixes, and proactive recommendations.

---

## Table of Contents
1. [Core Purpose & Problem Solved](#1-core-purpose--problem-solved)
2. [Marketplace Architecture](#2-marketplace-architecture)
3. [Skills Directory & Separation of Concerns](#3-skills-directory--separation-of-concerns)
4. [Entrypoint & Composition Pipeline](#4-entrypoint--composition-pipeline)
5. [Input & Output Schema](#5-input--output-schema)
6. [Detection Categories & Evidence Methodology](#6-detection-categories--evidence-methodology)
7. [Severity & Prioritization Model](#7-severity--prioritization-model)
8. [Safety, Politeness, and Guardrails](#8-safety-politeness-and-guardrails)
9. [Crawl Strategy & Performance Budget](#9-crawl-strategy--performance-budget)
10. [Generalization to Unseen Sites](#10-generalization-to-unseen-sites)
11. [Installation & Quickstart](#11-installation--quickstart)
12. [Verification & Test Results](#12-verification--test-results)
13. [Known Limitations & Scope](#13-known-limitations--scope)

---

## 1. Core Purpose & Problem Solved

Modern search behavior has bifurcated into two interdependent phases:
1. **AI Synthesis & Retrieval**: Users ask AI assistants questions ("What is the best enterprise cloud management tool?", "How much does Product X cost?"). If a brand is crawl-blocked, trapped in client-side JavaScript, lacks schema.org structured data, or has contradictory pricing, AI models cannot cite it accurately.
2. **Visitor Engagement & Retention**: When an AI assistant does cite a source and refers a user to the website, or when a user discovers the site directly, the user evaluates the page in seconds. If the page lacks an immediate value proposition, presents navigation dead ends, or strands the user on a deep page without breadcrumbs, the visitor bounces immediately.

This marketplace encodes this reasoning into **6 reusable Agent Skills** following the standard `agentskills.io` specification.

---

## 2. Marketplace Architecture

The marketplace adheres strictly to the Adobe Round 3 convention:

```
Adobe/
├── marketplace.json                        # Top-level manifest (lists all skills + entrypoint)
├── README.md                               # Full technical documentation
├── audit.py                                # Root CLI convenience runner
├── requirements.txt                        # Lightweight dependencies
│
├── skills/
│   ├── audit-orchestrator/                 # [ENTRYPOINT: "entrypoint": true]
│   │   ├── SKILL.md                        # agentskills.io entrypoint skill spec
│   │   ├── scripts/
│   │   │   ├── orchestrate.py              # Pipeline controller & deduper
│   │   │   └── report_builder.py           # Strict Adobe schema serializer
│   │   └── references/
│   │       ├── architecture.md             # Composition flow
│   │       ├── deduplication_rules.md      # Root-cause clustering
│   │       ├── severity_model.md           # Critical / High / Medium rubric
│   │       ├── prioritization_matrix.md    # Impact x Reach / Effort matrix
│   │       └── proactive_catalog.md        # Beyond-defect proactive recommendations
│   │
│   ├── crawl-render-audit/
│   │   ├── SKILL.md                        # agentskills.io crawl skill spec
│   │   ├── scripts/                        # crawler.py, robots_checker.py, render_comparator.py
│   │   └── references/                     # crawl_rules.md, render_gap_heuristics.md
│   │
│   ├── structured-data-audit/
│   │   ├── SKILL.md                        # agentskills.io structured data spec
│   │   ├── scripts/                        # schema_extractor.py, schema_validator.py
│   │   └── references/                     # required_schemas.md, common_schema_errors.md
│   │
│   ├── freshness-corroboration/
│   │   ├── SKILL.md                        # agentskills.io freshness spec
│   │   ├── scripts/                        # temporal_extractor.py, corroboration_checker.py
│   │   └── references/                     # freshness_rubric.md
│   │
│   ├── entity-clarity-audit/
│   │   ├── SKILL.md                        # agentskills.io entity clarity spec
│   │   ├── scripts/                        # entity_extractor.py, disambiguation_rules.py
│   │   └── references/                     # entity_rubric.md
│   │
│   └── engagement-audit/
│       ├── SKILL.md                        # agentskills.io visitor engagement spec
│       ├── scripts/                        # engagement_analyzer.py, navigation_graph.py
│       └── references/                     # engagement_heuristics.md
│
└── tests/
    ├── test_marketplace_manifest.py       # Validates marketplace.json & single entrypoint
    ├── test_skill_specs.py                 # Validates SKILL.md agentskills.io compliance
    ├── test_crawl_render_audit.py          # Unit tests for crawlability & render gaps
    ├── test_structured_data_audit.py       # Unit tests for Schema.org & JSON-LD
    ├── test_freshness_corroboration.py     # Unit tests for dates & cross-page conflicts
    ├── test_entity_clarity_audit.py        # Unit tests for brand disambiguation
    ├── test_engagement_audit.py            # Unit tests for value prop, CTAs, dead ends
    ├── test_orchestrator_dedup.py          # Tests finding deduplication & synthesis
    ├── test_schema_conformance.py          # Strict test against Adobe JSON schema
    └── test_adversarial_cases.py           # False positive control on edge-case sites
```

---

## 3. Skills Directory & Separation of Concerns

Every skill represents a genuine separation of concerns without artificial padding:

| Skill ID | Responsibility | Key Checks Performed |
| :--- | :--- | :--- |
| **`audit-orchestrator`** *(Entrypoint)* | Pipeline coordination, deduplication, scoring, proactive injection, reporting | Validates scope, executes specialists, clusters root causes, enforces schema |
| **`crawl-render-audit`** | Machine reachability & render gaps | `robots.txt` AI blocks (`GPTBot`, `ClaudeBot`, `PerplexityBot`), empty SPA shells (`#root`), non-text fact locking (`<img>` without alt), `noindex` tags |
| **`structured-data-audit`** | Semantic markup & Schema.org | Missing `Product`/`Offer` on PDPs, missing `Organization` on homepage, JSON-LD syntax errors, price schema vs visible text mismatches |
| **`freshness-corroboration`** | Temporal validity & cross-page consistency | Stale copyright (>=2 yrs out of date), expired roadmaps ("Roadmap 2022"), cross-page pricing conflicts ($19 vs $49), uncorroborated superlative claims |
| **`entity-clarity-audit`** | Knowledge graph grounding & disambiguation | Brand name dictionary collisions ("Apex", "Focus"), unbranded page titles (`<title>Home</title>`), missing `sameAs` authority links (Wikidata, LinkedIn) |
| **`engagement-audit`** | On-site visitor orientation & retention | Above-the-fold value proposition (`<h1>`), conversion page CTAs, navigation dead ends, deep-page breadcrumb orientation |

Each skill implements **progressive disclosure**:
- `SKILL.md`: Concise, executable instructions adhering to the `agentskills.io` standard.
- `references/`: Domain checklists, heuristics, and mathematical scoring models.
- `scripts/`: Production-ready, deterministic Python implementations.

---

## 4. Entrypoint & Composition Pipeline

In `marketplace.json`:
```json
{
  "id": "audit-orchestrator",
  "path": "skills/audit-orchestrator",
  "entrypoint": true
}
```
`audit-orchestrator` is the **only** entrypoint.

### Execution Workflow
1. **Scope & Polite Crawl**: Crawls up to 12-15 high-value pages using BFS prioritization (Homepage > About > Products > Pricing > Contact) with strict timeouts.
2. **Specialist Execution**: Dispatches parsed page representations (`PageData`) to each specialist skill.
3. **Finding Deduplication**: Clusters multi-symptom defects stemming from identical root causes (e.g. merging missing `Organization` schema with missing `sameAs` links into a consolidated high-leverage entity finding).
4. **Severity & Priority Assignment**: Assigns deterministic severities (`critical`, `high`, `medium`) and calculates action priority using the $\frac{\text{Impact} \times \text{Reach}}{\text{Effort}}$ matrix.
5. **Proactive Improvements**: Recommends high-value enhancements (such as deploying `/llms.txt` or `FAQPage` schema) even where no explicit defect exists.
6. **Schema Validation & Output**: Serializes the final report and validates it against the Adobe schema.

---

## 5. Input & Output Schema

### Input
A single target website URL or domain (e.g. `https://example.com`).

### Output
The entrypoint emits the exact JSON structure defined in the Adobe problem statement:

```json
{
  "site": "sportco.example",
  "audited_at": "2026-09-06T18:30:00Z",
  "summary": {
    "total_findings": 4,
    "critical": 0,
    "high": 2,
    "medium": 2
  },
  "findings": [
    {
      "id": "F-001",
      "title": "No JSON-LD structured data on product pages (1/1 missing)",
      "severity": "high",
      "evidence": "Crawled 1 product pages; 1/1 contain no schema.org Product or Offer markup. Sample affected pages: https://sportco.example/products/running-shoes.",
      "suggested_action": {
        "summary": "Add valid schema.org Product and Offer JSON-LD to every product page, including name, description, image, price, priceCurrency, and availability.",
        "priority": "high"
      },
      "category": "structured-data"
    },
    {
      "id": "F-002",
      "title": "Proactive: Implement an /llms.txt AI documentation manifest",
      "severity": "medium",
      "evidence": "No /llms.txt manifest was detected on sportco.example. Modern AI search scrapers use llms.txt to efficiently parse core offerings.",
      "suggested_action": {
        "summary": "Publish an /llms.txt markdown file at the root domain summarizing your brand, primary products, and key documentation links.",
        "priority": "medium"
      },
      "category": "discoverability",
      "is_proactive": true
    }
  ]
}
```

---

## 6. Detection Categories & Evidence Methodology

Every finding is backed by **verifiable evidence**. Never vague generalities ("poor SEO"), always concrete observations:
- **Numerical Ratios**: "Crawled 12 product pages; 10/12 contain no schema.org markup."
- **Exact Quotes**: "Found references to past years presented as upcoming roadmap commitments: 'Roadmap 2022: Cloud edition launching in Q3 2022'."
- **Exact URLs & Status**: "GET https://example.com/robots.txt contains 'Disallow: /' for User-Agent: GPTBot."
- **DOM Observations**: "Found empty SPA mount container (`<div id='root'>`) with 12 words of readable text in initial HTML."

---

## 7. Severity & Prioritization Model

### Severity Rubric
- **`critical`**: Completely blinds AI retrieval engines or search crawlers from accessing the brand (e.g. `Disallow: /` across all bots, `noindex` on homepage, SPA with zero server-rendered content).
- **`high`**: Reachable, but AI cannot extract facts or human visitors cannot understand what is offered (e.g. missing `Product`/`Offer` schema on ecommerce pages, AI agents explicitly blocked, contradictory internal pricing, missing H1/value prop, unnavigable dead ends).
- **`medium`**: Increases cognitive friction or signals stale maintenance (e.g. stale copyright notice >= 2 years old, missing `sameAs` authority links, deep pages lacking breadcrumbs).

### Prioritization Formula
$$\text{Priority Score} = \frac{\text{Impact} \times \text{Reach}}{\text{Implementation Effort}}$$

---

## 8. Safety, Politeness, and Guardrails

The marketplace operates under non-negotiable safety guardrails:
- **100% Read-Only**: Only HTTP `GET` and `HEAD` requests are issued. Never `POST`, `PUT`, or `DELETE`.
- **No Live Modifications**: Operates strictly as an audit-and-report engine. Never edits CMS content, live code, or server settings.
- **No Form Submissions**: Analyzes forms in HTML but never submits user or test inputs.
- **Strict `robots.txt` Compliance**: Reads `/robots.txt` and immediately excludes any disallowed paths from the crawl queue.
- **No Authentication Bypassing**: Never accesses authenticated portals or attempts password bypass.

---

## 9. Crawl Strategy & Performance Budget

- **Target Execution Time**: < 60 seconds (well under the 5-minute hackathon limit).
- **Bounded Page Limit**: Maximum 12-15 pages per domain.
- **Priority BFS Traversal**: Samples high-value pages first (Homepage > About > Products > Pricing > Contact) to ensure high audit yield with minimal requests.
- **Strict Timeout**: 6.0 seconds per HTTP request.
- **Lightweight Footprint**: Package size is < 1 MB (no heavy ML weights; well within the 50 MB limit).

---

## 10. Generalization to Unseen Sites

The marketplace does not hardcode domains or memorize specific website structures:
1. **Dynamic Page Type Inference**: Analyzes URLs, titles, and HTML semantics to infer whether a page is an ecommerce product, corporate about page, documentation guide, or pricing table.
2. **Adaptive Schema Validation**: Never demands `Product` schema on a corporate consultancy site, and never demands `Article` schema on a simple landing page.
3. **Context-Aware Disambiguation**: Checks whether common brand names have accompanying sector descriptors before flagging ambiguity.

---

## 11. Installation & Quickstart

### Prerequisites
- Python 3.10+
- `pip install -r requirements.txt`

### Running an Audit
To audit any website from the command line:
```bash
# Basic audit
python audit.py --url https://example.com

# Audit with bounded page count and file output
python audit.py --url https://example.com --max-pages 10 --output report.json
```

### Running Individual Skills Standalone
Each skill script can also be executed independently:
```bash
# Audit crawlability & render gaps
python skills/crawl-render-audit/scripts/audit_crawl.py --url https://example.com

# Audit structured data & Schema.org
python skills/structured-data-audit/scripts/audit_schema.py --url https://example.com

# Audit freshness & cross-page consistency
python skills/freshness-corroboration/scripts/audit_freshness.py --url https://example.com

# Audit entity clarity & brand disambiguation
python skills/entity-clarity-audit/scripts/audit_entity.py --url https://example.com

# Audit on-site visitor engagement
python skills/engagement-audit/scripts/audit_engagement.py --url https://example.com
```

---

## 12. Verification & Test Results

The marketplace includes an extensive automated test suite covering manifest validation, `SKILL.md` format compliance, specialist analyzers, deduplication, schema conformance, and adversarial false-positive controls:

```bash
pytest -v
```

### Test Execution Summary
```
tests/test_adversarial_cases.py::test_no_product_schema_penalty_on_non_product_site PASSED
tests/test_adversarial_cases.py::test_common_word_with_strong_sector_clarity_not_flagged PASSED
tests/test_adversarial_cases.py::test_end_to_end_on_perfect_site_has_zero_critical_or_high_defects PASSED
tests/test_crawl_render_audit.py::test_robots_ai_agents_blocked PASSED
tests/test_crawl_render_audit.py::test_robots_wildcard_blocked PASSED
tests/test_crawl_render_audit.py::test_render_gap_detected_on_empty_spa PASSED
tests/test_crawl_render_audit.py::test_render_comparator_clean_on_perfect_site PASSED
tests/test_engagement_audit.py::test_missing_h1_on_homepage PASSED
tests/test_engagement_audit.py::test_missing_cta_on_conversion_page PASSED
tests/test_engagement_audit.py::test_navigation_dead_ends_detected PASSED
tests/test_engagement_audit.py::test_deep_page_missing_breadcrumbs PASSED
tests/test_engagement_audit.py::test_perfect_site_engagement_passes PASSED
tests/test_entity_clarity_audit.py::test_unbranded_titles_detected PASSED
tests/test_entity_clarity_audit.py::test_common_dictionary_brand_collision_risk PASSED
tests/test_entity_clarity_audit.py::test_perfect_entity_signals_pass PASSED
tests/test_freshness_corroboration.py::test_stale_copyright_and_roadmap_detected PASSED
tests/test_freshness_corroboration.py::test_cross_page_pricing_contradiction_detected PASSED
tests/test_freshness_corroboration.py::test_fresh_site_passes_cleanly PASSED
tests/test_marketplace_manifest.py::test_marketplace_json_exists_and_valid PASSED
tests/test_marketplace_manifest.py::test_exactly_one_entrypoint PASSED
tests/test_marketplace_manifest.py::test_all_skill_paths_and_skills_exist PASSED
tests/test_orchestrator_dedup.py::test_entity_schema_and_authority_merging PASSED
tests/test_schema_conformance.py::test_adobe_sample_schema_conformance PASSED
tests/test_skill_specs.py::test_skill_md_agentskills_compliance (all 6 skills) PASSED
tests/test_skill_specs.py::test_skill_progressive_disclosure_structure (all 6 skills) PASSED
tests/test_structured_data_audit.py::test_missing_product_schema_flagged_with_evidence PASSED
tests/test_structured_data_audit.py::test_valid_product_schema_passes_cleanly PASSED
tests/test_structured_data_audit.py::test_jsonld_syntax_error_detected PASSED
tests/test_structured_data_audit.py::test_homepage_organization_schema_detection PASSED

============================= 39 passed in 2.62s ==============================
```

---

## 13. Known Limitations & Scope

1. **Lightweight Headless Footprint**: To maintain a fast runtime (< 60s) and package size (< 1 MB) without bulky Chromium binaries, the default crawler audits initial raw HTTP responses (which mimics how the majority of AI search bots and web scrapers index the web). For heavy client-rendered SPAs, it detects the empty container as a high/critical render gap rather than rendering JavaScript.
2. **Paywalls & Cloudflare CAPTCHAs**: Sites protected behind Cloudflare Turnstile, perimeter CAPTCHAs, or hard login walls will be reported as unreachable or access-restricted rather than guessing contents.
3. **External Corroboration**: To avoid fabricating evidence or violating third-party search engine terms of service, corroboration checks focus on internal cross-page contradictions and verified external link anchors (`sameAs`, review badge links).

